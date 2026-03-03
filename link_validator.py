#!/usr/bin/env python3
"""
CMACED Startup Intelligence Dashboard – Link Validator
Superior University × ID92

Validates all application links in opportunities.json:
- Checks HTTP status (must be 200)
- Removes broken links (404, 403, 500, timeout)
- Archives expired entries (deadline passed)
- Updates status fields
- Deduplicates entries
"""

import json
import logging
import time
from datetime import datetime, date
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
OPP_FILE = BASE_DIR / 'opportunities.json'
ARCH_FILE = BASE_DIR / 'archive.json'
LOG_FILE  = BASE_DIR / 'scraper' / 'validation.log'

TODAY     = datetime.utcnow().date()
HEADERS   = {
    'User-Agent': 'Mozilla/5.0 (compatible; CMACED-Validator/1.0; +https://superior.edu.pk)',
}
TIMEOUT   = 12
MAX_WORKERS = 6


# ─── Helpers ──────────────────────────────────────────────────────────────────
def load_json(path: Path) -> list:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return data if isinstance(data, list) else []
        except Exception as e:
            log.error(f'Failed to load {path}: {e}')
    return []


def save_json(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    log.info(f'Saved {len(data)} entries → {path}')


def check_link(url: str) -> bool:
    """Return True if URL responds HTTP 200."""
    if not url or not url.startswith('http'):
        return False
    try:
        resp = requests.head(
            url, headers=HEADERS, timeout=TIMEOUT,
            allow_redirects=True
        )
        if resp.status_code == 200:
            return True
        if resp.status_code in (405, 406):
            # HEAD not allowed — try GET
            resp2 = requests.get(
                url, headers=HEADERS, timeout=TIMEOUT,
                allow_redirects=True, stream=True
            )
            resp2.close()
            return resp2.status_code == 200
        return False
    except Exception:
        return False


def parse_deadline(dl_str: str):
    """Return date object or None."""
    if not dl_str:
        return None
    try:
        return date.fromisoformat(dl_str[:10])
    except ValueError:
        return None


def compute_status(entry: dict) -> str:
    """Compute status string for an entry."""
    dl = parse_deadline(entry.get('deadline', ''))
    if not dl:
        return 'Open'
    if dl < TODAY:
        return 'Closed'
    delta = (dl - TODAY).days
    if delta <= 7:
        return 'Closing Soon'

    added = entry.get('date_added', '')
    try:
        added_date = date.fromisoformat(added[:10])
        if (TODAY - added_date).days <= 2:
            return 'New'
    except Exception:
        pass

    return 'Open'


# ─── Validation ───────────────────────────────────────────────────────────────
def validate_entry(entry: dict) -> dict:
    """Validate a single entry. Returns updated entry with _valid and _expired flags."""
    link = entry.get('application_link', '')
    result = entry.copy()

    link_ok = check_link(link)
    result['_valid'] = link_ok

    dl = parse_deadline(entry.get('deadline', ''))
    result['_expired'] = bool(dl and dl < TODAY)
    result['status'] = compute_status(entry)

    if not link_ok:
        log.warning(f'  ✗ Broken link [{entry.get("id","")}]: {link}')
    else:
        log.info(f'  ✓ OK [{entry.get("id","")}]')

    return result


def deduplicate(entries: list) -> list:
    """Remove duplicate IDs, keeping most recently added."""
    seen = {}
    for e in entries:
        eid = e.get('id', '')
        if eid not in seen:
            seen[eid] = e
        else:
            # Keep the one with the newer date_added
            old_date = seen[eid].get('date_added', '')
            new_date = e.get('date_added', '')
            if new_date > old_date:
                seen[eid] = e
    return list(seen.values())


# ─── Main ─────────────────────────────────────────────────────────────────────
def run():
    opportunities = load_json(OPP_FILE)
    archive       = load_json(ARCH_FILE)

    if not opportunities:
        log.warning('No opportunities to validate.')
        return

    log.info(f'Validating {len(opportunities)} opportunities…')

    validated = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(validate_entry, e): e for e in opportunities}
        for fut in as_completed(futures):
            try:
                validated.append(fut.result())
            except Exception as err:
                entry = futures[fut]
                log.error(f'Validation error for {entry.get("id","?")}: {err}')
                entry['_valid'] = False
                entry['_expired'] = False
                entry['status'] = 'Open'
                validated.append(entry)

    # Separate: valid+active vs expired/broken
    active_entries = []
    to_archive     = []
    removed_log    = []

    for e in validated:
        clean = {k: v for k, v in e.items() if not k.startswith('_')}
        if e.get('_expired'):
            clean['status'] = 'Closed'
            to_archive.append(clean)
            removed_log.append(f"ARCHIVED (expired): {e.get('id')} – deadline {e.get('deadline')}")
        elif not e.get('_valid'):
            removed_log.append(f"REMOVED (broken link): {e.get('id')} – {e.get('application_link')}")
        else:
            active_entries.append(clean)

    # Merge archive (deduplicate)
    archive_ids = {a['id'] for a in archive}
    for entry in to_archive:
        if entry['id'] not in archive_ids:
            archive.append(entry)

    # Deduplicate
    active_entries = deduplicate(active_entries)
    archive        = deduplicate(archive)

    # Save
    save_json(OPP_FILE, active_entries)
    save_json(ARCH_FILE, archive)

    # Log report
    log.info(f'\n{"="*50}')
    log.info(f'Validation Report – {TODAY}')
    log.info(f'  Active opportunities: {len(active_entries)}')
    log.info(f'  Archived (expired):   {len(to_archive)}')
    log.info(f'  Removed (broken):     {sum(1 for r in removed_log if "REMOVED" in r)}')
    if removed_log:
        log.info('  Details:')
        for r in removed_log:
            log.info(f'    {r}')
    log.info('='*50)

    # Write log file
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f'\n[{datetime.utcnow().isoformat()}] Validation run\n')
        for r in removed_log:
            f.write(f'  {r}\n')
        f.write(f'  Active: {len(active_entries)}, Archive: {len(archive)}\n')

    log.info('Validation complete.')


if __name__ == '__main__':
    run()
