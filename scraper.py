#!/usr/bin/env python3
"""
CMACED Startup Intelligence Dashboard – Scraper
Superior University × ID92
Scrapes official program pages only. No paid APIs.
"""

import json
import re
import uuid
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
OPP_FILE = BASE_DIR / 'opportunities.json'
ARCH_FILE = BASE_DIR / 'archive.json'

TODAY = datetime.utcnow().date()
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (compatible; CMACED-Bot/1.0; +https://superior.edu.pk)'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# ─── Source Registry ──────────────────────────────────────────────────────────
SOURCES = [
    # ── Pakistan Government ────────────────────────────────────────────────
    {
        'id': 'ignite',
        'name': 'Ignite National Technology Fund',
        'url': 'https://ignite.org.pk/programs/',
        'region': 'national',
        'country': 'Pakistan',
        'type': 'grant',
        'fallback': {
            'id': 'ignite-startup-fund',
            'name': 'Ignite Startup Fund',
            'organization': 'Ignite National Technology Fund',
            'type': 'grant',
            'country': 'Pakistan',
            'region': 'national',
            'deadline': '',
            'prize': 'PKR 5–25 million',
            'requirements': 'Early-stage tech startups registered in Pakistan. Working prototype required.',
            'application_link': 'https://ignite.org.pk/programs/',
            'source': 'https://ignite.org.pk',
        }
    },
    {
        'id': 'plan9',
        'name': 'Plan9 – PITB Incubator',
        'url': 'https://plan9.pitb.gov.pk',
        'region': 'national',
        'country': 'Pakistan',
        'type': 'accelerator',
        'fallback': {
            'id': 'plan9-incubator',
            'name': 'Plan9 Incubation Program',
            'organization': 'PITB – Punjab Information Technology Board',
            'type': 'accelerator',
            'country': 'Pakistan',
            'region': 'national',
            'deadline': '',
            'prize': 'Office space + PKR 1M seed',
            'requirements': 'Tech-based startup teams from Punjab. Pre-revenue or early revenue stage.',
            'application_link': 'https://plan9.pitb.gov.pk',
            'source': 'https://plan9.pitb.gov.pk',
        }
    },
    {
        'id': 'stza-nic',
        'name': 'National Incubation Centers – STZA',
        'url': 'https://niclahore.com',
        'region': 'national',
        'country': 'Pakistan',
        'type': 'accelerator',
        'fallback': {
            'id': 'nic-lahore',
            'name': 'National Incubation Center Lahore',
            'organization': 'NIC Lahore / STZA',
            'type': 'accelerator',
            'country': 'Pakistan',
            'region': 'national',
            'deadline': '',
            'prize': 'USD 10,000 + mentorship',
            'requirements': 'Pakistani founders. Tech/innovation focused. Presentation to panel required.',
            'application_link': 'https://niclahore.com',
            'source': 'https://niclahore.com',
        }
    },
    {
        'id': 'hec',
        'name': 'HEC Innovation Programs',
        'url': 'https://hec.gov.pk/english/services/faculty/NRPU/Pages/Default.aspx',
        'region': 'national',
        'country': 'Pakistan',
        'type': 'grant',
        'fallback': {
            'id': 'hec-innovation-fund',
            'name': 'HEC Innovation & Research Fund',
            'organization': 'Higher Education Commission Pakistan',
            'type': 'grant',
            'country': 'Pakistan',
            'region': 'national',
            'deadline': '',
            'prize': 'PKR 2–10 million',
            'requirements': 'University-affiliated researchers and student entrepreneurs in Pakistan.',
            'application_link': 'https://hec.gov.pk/english/services/faculty/NRPU/Pages/Default.aspx',
            'source': 'https://hec.gov.pk',
        }
    },
    {
        'id': 'pseb',
        'name': 'PSEB Startup Support',
        'url': 'https://pseb.org.pk/startups',
        'region': 'national',
        'country': 'Pakistan',
        'type': 'grant',
        'fallback': {
            'id': 'pseb-ites-support',
            'name': 'PSEB IT Export Startup Support',
            'organization': 'Pakistan Software Export Board',
            'type': 'grant',
            'country': 'Pakistan',
            'region': 'national',
            'deadline': '',
            'prize': 'PKR 3 million + export facilitation',
            'requirements': 'IT/software companies targeting export markets. Must be PSEB registered.',
            'application_link': 'https://pseb.org.pk/startups',
            'source': 'https://pseb.org.pk',
        }
    },
    # ── Pakistan Universities ──────────────────────────────────────────────
    {
        'id': 'cmaced',
        'name': 'CMACED Superior University Programs',
        'url': 'https://superior.edu.pk',
        'region': 'national',
        'country': 'Pakistan',
        'type': 'grant',
        'fallback': {
            'id': 'cmaced-startup-grant',
            'name': 'CMACED Internal Startup Grant',
            'organization': 'CMACED – Superior University',
            'type': 'grant',
            'country': 'Pakistan',
            'region': 'national',
            'deadline': '',
            'prize': 'PKR 500,000',
            'requirements': 'Currently enrolled Superior University students. Working prototype required.',
            'application_link': 'https://superior.edu.pk',
            'source': 'https://superior.edu.pk',
        }
    },
    {
        'id': 'lums',
        'name': 'LUMS Centre for Entrepreneurship',
        'url': 'https://lums.edu.pk/centre-entrepreneurship',
        'region': 'national',
        'country': 'Pakistan',
        'type': 'accelerator',
        'fallback': {
            'id': 'lums-entrepreneurship',
            'name': 'LUMS Centre for Entrepreneurship Program',
            'organization': 'LUMS – Lahore University of Management Sciences',
            'type': 'accelerator',
            'country': 'Pakistan',
            'region': 'national',
            'deadline': '',
            'prize': 'Mentorship + USD 5,000 seed',
            'requirements': 'Open to all Pakistani university graduates and students.',
            'application_link': 'https://lums.edu.pk/centre-entrepreneurship',
            'source': 'https://lums.edu.pk',
        }
    },
    # ── International ──────────────────────────────────────────────────────
    {
        'id': 'yc',
        'name': 'Y Combinator',
        'url': 'https://www.ycombinator.com/apply',
        'region': 'international',
        'country': 'USA',
        'type': 'accelerator',
        'fallback': {
            'id': 'yc-accelerator',
            'name': 'Y Combinator Accelerator Program',
            'organization': 'Y Combinator',
            'type': 'accelerator',
            'country': 'USA',
            'region': 'international',
            'deadline': '',
            'prize': 'USD 500,000',
            'requirements': 'Any stage, any country. Online application open. Equity-based investment.',
            'application_link': 'https://www.ycombinator.com/apply',
            'source': 'https://www.ycombinator.com',
        }
    },
    {
        'id': 'hult',
        'name': 'Hult Prize',
        'url': 'https://www.hultprize.org',
        'region': 'international',
        'country': 'Global',
        'type': 'competition',
        'fallback': {
            'id': 'hult-prize',
            'name': 'Hult Prize Global Competition',
            'organization': 'Hult Prize Foundation',
            'type': 'competition',
            'country': 'Global',
            'region': 'international',
            'deadline': '',
            'prize': 'USD 1,000,000',
            'requirements': 'University student teams. Social impact focus. Virtual application open worldwide.',
            'application_link': 'https://www.hultprize.org',
            'source': 'https://www.hultprize.org',
        }
    },
    {
        'id': 'mit-solve',
        'name': 'MIT Solve',
        'url': 'https://solve.mit.edu',
        'region': 'international',
        'country': 'Global',
        'type': 'competition',
        'fallback': {
            'id': 'mit-solve-challenge',
            'name': 'MIT Solve Global Challenge',
            'organization': 'MIT Solve',
            'type': 'competition',
            'country': 'Global',
            'region': 'international',
            'deadline': '',
            'prize': 'USD 10,000–150,000',
            'requirements': 'Social entrepreneurs worldwide. Online application accepted from Pakistan.',
            'application_link': 'https://solve.mit.edu',
            'source': 'https://solve.mit.edu',
        }
    },
    {
        'id': 'google-startups',
        'name': 'Google for Startups Accelerator',
        'url': 'https://startup.google.com/programs/accelerator/',
        'region': 'international',
        'country': 'Global',
        'type': 'accelerator',
        'fallback': {
            'id': 'google-startups-accelerator',
            'name': 'Google for Startups Accelerator',
            'organization': 'Google',
            'type': 'accelerator',
            'country': 'Global',
            'region': 'international',
            'deadline': '',
            'prize': 'USD 100,000 in Cloud credits (equity-free)',
            'requirements': 'Series A or earlier. AI/ML focused preferred. Virtual participation available.',
            'application_link': 'https://startup.google.com/programs/accelerator/',
            'source': 'https://startup.google.com',
        }
    },
    {
        'id': 'microsoft-startups',
        'name': 'Microsoft for Startups Founders Hub',
        'url': 'https://www.microsoft.com/en-us/startups',
        'region': 'international',
        'country': 'Global',
        'type': 'grant',
        'fallback': {
            'id': 'msft-founders-hub',
            'name': 'Microsoft for Startups Founders Hub',
            'organization': 'Microsoft',
            'type': 'grant',
            'country': 'Global',
            'region': 'international',
            'deadline': '',
            'prize': 'USD 150,000 in Azure credits',
            'requirements': 'Pre-seed to Series A. No equity required. Open to Pakistan-based startups.',
            'application_link': 'https://www.microsoft.com/en-us/startups',
            'source': 'https://www.microsoft.com/en-us/startups',
        }
    },
    {
        'id': 'seedstars',
        'name': 'Seedstars World',
        'url': 'https://www.seedstars.com/programs/',
        'region': 'international',
        'country': 'Global',
        'type': 'competition',
        'fallback': {
            'id': 'seedstars-world',
            'name': 'Seedstars World Competition',
            'organization': 'Seedstars World',
            'type': 'competition',
            'country': 'Global',
            'region': 'international',
            'deadline': '',
            'prize': 'USD 500,000 investment',
            'requirements': 'Early-stage tech startups. Local qualifying rounds then global finals.',
            'application_link': 'https://www.seedstars.com/programs/',
            'source': 'https://www.seedstars.com',
        }
    },
    {
        'id': 'masschallenge',
        'name': 'MassChallenge',
        'url': 'https://masschallenge.org',
        'region': 'international',
        'country': 'Global',
        'type': 'accelerator',
        'fallback': {
            'id': 'masschallenge-accelerator',
            'name': 'MassChallenge Global Accelerator',
            'organization': 'MassChallenge',
            'type': 'accelerator',
            'country': 'Global',
            'region': 'international',
            'deadline': '',
            'prize': 'USD 250,000 equity-free',
            'requirements': 'No equity taken. Open to international founders including Pakistan.',
            'application_link': 'https://masschallenge.org',
            'source': 'https://masschallenge.org',
        }
    },
    {
        'id': 'devpost',
        'name': 'Devpost Hackathons',
        'url': 'https://devpost.com/hackathons',
        'region': 'international',
        'country': 'Global',
        'type': 'hackathon',
        'fallback': {
            'id': 'devpost-hackathons',
            'name': 'Devpost Global Hackathons',
            'organization': 'Devpost',
            'type': 'hackathon',
            'country': 'Global',
            'region': 'international',
            'deadline': '',
            'prize': 'Varies per hackathon',
            'requirements': 'Virtual. Open to all nationalities. Individual or team submission.',
            'application_link': 'https://devpost.com/hackathons',
            'source': 'https://devpost.com',
        }
    },
]


# ─── Scraper ──────────────────────────────────────────────────────────────────
def fetch_page(url: str, timeout: int = 15) -> BeautifulSoup | None:
    """Fetch URL and return BeautifulSoup or None."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, 'html.parser')
        log.warning(f'HTTP {resp.status_code} for {url}')
    except Exception as e:
        log.warning(f'Fetch error {url}: {e}')
    return None


def extract_deadline(soup: BeautifulSoup, url: str) -> str:
    """Try to extract a deadline date from page content."""
    date_patterns = [
        r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b',
        r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',
        r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b',
        r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
    ]
    deadline_keywords = ['deadline', 'apply by', 'last date', 'closes', 'due date', 'submission date']

    text = soup.get_text(' ', strip=True) if soup else ''
    text_lower = text.lower()

    for kw in deadline_keywords:
        idx = text_lower.find(kw)
        if idx != -1:
            snippet = text[idx:idx+120]
            for pat in date_patterns:
                m = re.search(pat, snippet, re.IGNORECASE)
                if m:
                    parsed = parse_date_str(m.group(1))
                    if parsed:
                        return parsed

    return ''


def parse_date_str(s: str) -> str:
    """Try multiple date formats, return ISO string or empty."""
    formats = [
        '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
        '%d %B %Y', '%B %d %Y', '%B %d, %Y',
        '%d %b %Y', '%b %d %Y', '%b %d, %Y',
    ]
    s = s.strip().replace(',', '')
    for fmt in formats:
        try:
            d = datetime.strptime(s, fmt).date()
            # Only accept future or recent dates
            if d >= TODAY - timedelta(days=30):
                return d.isoformat()
        except ValueError:
            pass
    return ''


def scrape_source(src: dict) -> dict:
    """Scrape a single source and return opportunity dict."""
    log.info(f"Scraping: {src['name']} – {src['url']}")
    soup = fetch_page(src['url'])
    fallback = src['fallback']

    entry = {
        'id': fallback['id'],
        'name': fallback['name'],
        'organization': fallback['organization'],
        'type': fallback['type'],
        'country': fallback['country'],
        'region': fallback['region'],
        'deadline': fallback.get('deadline', ''),
        'prize': fallback.get('prize', ''),
        'requirements': fallback.get('requirements', ''),
        'application_link': fallback['application_link'],
        'source': fallback['source'],
        'date_added': TODAY.isoformat(),
        'status': 'Open',
    }

    if soup:
        # Try to extract deadline
        deadline = extract_deadline(soup, src['url'])
        if deadline:
            entry['deadline'] = deadline
            log.info(f"  → Found deadline: {deadline}")

        # Try to find a more specific apply link
        apply_link = find_apply_link(soup, src['url'])
        if apply_link:
            entry['application_link'] = apply_link

    return entry


def find_apply_link(soup: BeautifulSoup, base_url: str) -> str:
    """Find the most likely apply/apply-now link on the page."""
    keywords = ['apply now', 'apply here', 'apply online', 'register now', 'submit application']
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True).lower()
        href = a['href']
        if any(kw in text for kw in keywords) and href:
            full = urljoin(base_url, href)
            if full.startswith('http'):
                return full
    return ''


# ─── Main ─────────────────────────────────────────────────────────────────────
def load_json(path: Path) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8')) or []
        except Exception:
            pass
    return []


def save_json(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    log.info(f'Saved {len(data)} entries → {path}')


def run():
    existing = {o['id']: o for o in load_json(OPP_FILE)}
    archive  = {o['id']: o for o in load_json(ARCH_FILE)}

    fresh = {}
    for src in SOURCES:
        try:
            entry = scrape_source(src)
            time.sleep(1.5)  # polite delay

            # Preserve original date_added if we've seen this before
            old = existing.get(entry['id'])
            if old and old.get('date_added'):
                entry['date_added'] = old['date_added']

            fresh[entry['id']] = entry
        except Exception as e:
            log.error(f"Error scraping {src['name']}: {e}")
            # Use fallback
            fb = src['fallback'].copy()
            fb['date_added'] = TODAY.isoformat()
            fb['status'] = 'Open'
            fresh[fb['id']] = fb

    log.info(f'Scraped {len(fresh)} entries')
    save_json(OPP_FILE, list(fresh.values()))
    save_json(ARCH_FILE, list(archive.values()))
    log.info('Scraper complete.')


if __name__ == '__main__':
    run()
