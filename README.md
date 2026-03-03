# CMACED – Startup Intelligence Dashboard
### Superior University × ID92

> Official startup opportunity intelligence platform for CMACED – Superior University, powered by ID92.
> Curated grants, accelerators, competitions & fellowships — verified in real time.

---

## Overview

This is a **production-grade, static dashboard** hosted on GitHub Pages, updated daily via GitHub Actions. It aggregates startup opportunities from official Pakistani and international sources, validates all links every 24 hours, and automatically archives expired programs.

**No paid APIs. No external databases. No Node servers.**

---

## Project Structure

```
cmaced-startup-dashboard/
├── index.html               ← Main dashboard UI
├── style.css                ← Styles (dark mode, responsive)
├── script.js                ← Dashboard logic & CSV export
├── opportunities.json       ← Active opportunities (auto-updated)
├── archive.json             ← Expired opportunities archive
│
├── scraper/
│   ├── scraper.py           ← Main scraper (official sources only)
│   ├── link_validator.py    ← Link checker + archiver
│   ├── requirements.txt     ← Python dependencies
│   └── validation.log       ← Auto-generated log
│
├── .github/workflows/
│   └── auto-update.yml      ← Daily GitHub Actions workflow
│
└── README.md
```

---

## Setup & Deployment

### 1. Fork / Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/cmaced-startup-dashboard.git
cd cmaced-startup-dashboard
```

### 2. Enable GitHub Pages

1. Go to **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / root (`/`)
4. Click **Save**

Your dashboard will be live at:
`https://YOUR_ORG.github.io/cmaced-startup-dashboard/`

### 3. Enable GitHub Actions

1. Go to **Settings → Actions → General**
2. Under "Workflow permissions", select **Read and write permissions**
3. Click **Save**

The daily automation is now active.

### 4. Run Initial Scrape (Optional but recommended)

Trigger a manual run from **Actions → Daily Update → Run workflow**.

---

## How Automation Works

The GitHub Actions workflow (`auto-update.yml`) runs daily at **00:00 UTC**:

```
1. Checkout repository
2. Install Python dependencies (requests, beautifulsoup4)
3. Run scraper.py       → scrapes official program pages → writes opportunities.json
4. Run link_validator.py → validates all links → archives expired → deduplicates
5. Commit changes       → auto-commits updated JSON files if anything changed
```

You can also trigger it manually from the **Actions** tab at any time.

---

## How Link Validation Works

`link_validator.py` runs after every scrape:

- **HTTP check**: Every `application_link` receives a HEAD request (falls back to GET).
- **Broken links** (non-200 responses, timeouts): Entry is **removed** from `opportunities.json` and logged.
- **Expired deadlines** (deadline date < today): Entry is moved to `archive.json` with `status: "Closed"`.
- **Deduplication**: Duplicate IDs are removed, keeping the most recently added version.
- **Status recalculation**:
  - `New` → added within last 48 hours
  - `Closing Soon` → deadline within 7 days
  - `Open` → active, deadline in the future
  - `Closed` → deadline passed (archived)

No broken URLs will ever appear on the live dashboard.

---

## How to Add New Sources

Open `scraper/scraper.py` and add an entry to the `SOURCES` list:

```python
{
    'id': 'unique-source-id',
    'name': 'Program Display Name',
    'url': 'https://official-program-page.org/apply',
    'region': 'national',        # 'national' or 'international'
    'country': 'Pakistan',
    'type': 'grant',             # grant | accelerator | competition | hackathon | fellowship
    'fallback': {
        'id': 'unique-entry-id',
        'name': 'Full Program Name',
        'organization': 'Organization Name',
        'type': 'grant',
        'country': 'Pakistan',
        'region': 'national',
        'deadline': '',           # Leave empty; scraper will try to extract
        'prize': 'PKR X million',
        'requirements': 'Who can apply and what is required.',
        'application_link': 'https://official-apply-link.org',
        'source': 'https://official-source.org',
    }
},
```

**Rules for adding sources:**
- URL must be an official program/organization website
- No social media, news aggregators, or unofficial pages
- Verify manually that the link is live before adding
- Prize amounts must be from official sources only
- If prize is unconfirmed, leave it empty or write "Not specified"

---

## Data Format

### `opportunities.json`

```json
[
  {
    "id": "unique-slug-id",
    "name": "Program Name",
    "organization": "Org Name",
    "type": "grant | competition | accelerator | hackathon | fellowship",
    "country": "Pakistan",
    "region": "national | international",
    "deadline": "2025-12-31",
    "prize": "USD 10,000",
    "requirements": "Who can apply.",
    "application_link": "https://apply.example.com",
    "source": "https://official.example.com",
    "date_added": "2025-06-01",
    "status": "Open | New | Closing Soon | Closed"
  }
]
```

### `archive.json`

Same format — contains expired/closed programs.

---

## Archive Export

The dashboard includes a **Download Archive (CSV)** button that:

1. Reads all entries from `archive.json` + closed `opportunities.json` entries
2. Generates a `.csv` file with all fields
3. Names it `cmaced-archive-YYYY.csv`
4. Triggers a browser download

This works fully client-side on GitHub Pages — no server required.

---

## Dashboard Features

| Feature | Description |
|---|---|
| Live stats | Total, National, International, Closing Soon, New |
| Tabs | All, National 🇵🇰, International 🌍, Grants, Competitions, Hackathons, Accelerators, Fellowships, Closing Soon, Archive |
| Search | Full-text search across name, organization, requirements |
| Sort | By deadline, newest, prize amount |
| Dark mode | Toggle with localStorage persistence |
| Mobile responsive | Fully responsive grid layout |
| CSV export | Download archive as CSV |
| Countdown badges | Days remaining for closing-soon entries |
| Detail modal | Click any card for full program details |
| Link safety | No 404 links ever shown; all validated daily |

---

## Data Sources

### Pakistan – Government
- Ignite National Technology Fund → ignite.org.pk
- Plan9 / PITB → plan9.pitb.gov.pk
- National Incubation Centers → niclahore.com
- HEC Innovation Programs → hec.gov.pk
- PSEB → pseb.org.pk

### Pakistan – Universities
- CMACED Superior University → superior.edu.pk
- LUMS Centre for Entrepreneurship → lums.edu.pk

### International (Virtual Apply Available)
- Y Combinator → ycombinator.com
- Hult Prize → hultprize.org
- MIT Solve → solve.mit.edu
- Google for Startups → startup.google.com
- Microsoft for Startups → microsoft.com/en-us/startups
- Seedstars World → seedstars.com
- MassChallenge → masschallenge.org
- Devpost Hackathons → devpost.com

---

## Adding Logos

Place logo files in the root directory:

- `cmaced-logo.png` — CMACED logo
- `superior-logo.png` — Superior University logo
- `id92-logo.png` — ID92 logo

Then update `index.html` to replace the text logos with `<img>` tags.

---

## Local Development

```bash
# Serve locally (Python)
python3 -m http.server 8080
# Open http://localhost:8080

# Run scraper locally
cd scraper
pip install -r requirements.txt
python scraper.py
python link_validator.py
```

---

## Institutional Notes

- All data sourced **exclusively** from official program websites
- No social media, RSS feeds, or news article links are stored
- Broken links are removed automatically within 24 hours
- No fabricated deadlines, prize amounts, or requirements
- Unverifiable entries are never displayed

---

**CMACED – Superior University × ID92**
Startup Intelligence Dashboard
Lahore, Pakistan
