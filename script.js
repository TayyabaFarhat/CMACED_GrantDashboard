/* ============================================================
   CMACED – Startup Intelligence Dashboard
   script.js | Superior University × ID92
   ============================================================ */

'use strict';

// ── State ──────────────────────────────────────────────────
const State = {
  opportunities: [],
  archive: [],
  activeTab: 'all',
  searchQuery: '',
  sortBy: 'deadline',
};

// ── DOM Refs ───────────────────────────────────────────────
const $ = id => document.getElementById(id);
const grid       = $('opportunitiesGrid');
const emptyState = $('emptyState');
const searchInput= $('searchInput');
const searchClear= $('searchClear');
const sortSelect = $('sortSelect');
const modalOverlay= $('modalOverlay');
const modalContent= $('modalContent');

// ── Init ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadData();
  bindEvents();
});

// ── Theme ──────────────────────────────────────────────────
function initTheme() {
  const saved = localStorage.getItem('cmaced-theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
}
$('themeToggle').addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('cmaced-theme', next);
});

// ── Data Loading ───────────────────────────────────────────
async function loadData() {
  try {
    const [oppRes, archRes] = await Promise.allSettled([
      fetch('opportunities.json?' + Date.now()),
      fetch('archive.json?' + Date.now()),
    ]);

    if (oppRes.status === 'fulfilled' && oppRes.value.ok) {
      const data = await oppRes.value.json();
      State.opportunities = Array.isArray(data) ? data : (data.opportunities || []);
    } else {
      State.opportunities = getSampleData();
    }

    if (archRes.status === 'fulfilled' && archRes.value.ok) {
      const data = await archRes.value.json();
      State.archive = Array.isArray(data) ? data : (data.opportunities || []);
    } else {
      State.archive = [];
    }

  } catch (e) {
    console.warn('Using sample data:', e.message);
    State.opportunities = getSampleData();
  }

  updateStats();
  render();
  updateLastUpdated();
}

function updateLastUpdated() {
  const el = $('lastUpdatedText');
  if (!el) return;
  const now = new Date();
  el.textContent = 'Updated ' + now.toLocaleDateString('en-PK', {
    day: 'numeric', month: 'short', year: 'numeric'
  });
}

// ── Stats ──────────────────────────────────────────────────
function updateStats() {
  const all = State.opportunities;
  const today = new Date();
  const in7   = new Date(today.getTime() + 7 * 86400000);
  const in48h = new Date(today.getTime() - 48 * 3600000);

  $('statTotal').textContent   = all.length;
  $('statNational').textContent= all.filter(o => o.region === 'national').length;
  $('statIntl').textContent    = all.filter(o => o.region === 'international').length;
  $('statClosing').textContent = all.filter(o => {
    if (!o.deadline) return false;
    const d = new Date(o.deadline);
    return d >= today && d <= in7;
  }).length;
  $('statNew').textContent = all.filter(o => {
    if (!o.date_added) return false;
    return new Date(o.date_added) >= in48h;
  }).length;
}

// ── Filter / Sort ──────────────────────────────────────────
function getFilteredData() {
  const tab   = State.activeTab;
  const query = State.searchQuery.toLowerCase();
  let pool    = tab === 'archive' ? State.archive : State.opportunities;

  if (tab === 'national')      pool = pool.filter(o => o.region === 'national');
  else if (tab === 'international') pool = pool.filter(o => o.region === 'international');
  else if (tab === 'closing')  {
    const today = new Date();
    const in7   = new Date(today.getTime() + 7 * 86400000);
    pool = pool.filter(o => {
      if (!o.deadline) return false;
      const d = new Date(o.deadline);
      return d >= today && d <= in7;
    });
  } else if (['grant','competition','hackathon','accelerator','fellowship'].includes(tab)) {
    pool = pool.filter(o => o.type === tab);
  }

  if (query) {
    pool = pool.filter(o =>
      (o.name || '').toLowerCase().includes(query) ||
      (o.organization || '').toLowerCase().includes(query) ||
      (o.requirements || '').toLowerCase().includes(query)
    );
  }

  // Sort
  const sorted = [...pool];
  if (State.sortBy === 'deadline') {
    sorted.sort((a, b) => {
      if (!a.deadline) return 1;
      if (!b.deadline) return -1;
      return new Date(a.deadline) - new Date(b.deadline);
    });
  } else if (State.sortBy === 'new') {
    sorted.sort((a, b) => new Date(b.date_added || 0) - new Date(a.date_added || 0));
  } else if (State.sortBy === 'prize') {
    sorted.sort((a, b) => parsePrize(b.prize) - parsePrize(a.prize));
  }

  return sorted;
}

function parsePrize(str) {
  if (!str) return 0;
  const m = str.replace(/,/g, '').match(/[\d.]+/);
  return m ? parseFloat(m[0]) : 0;
}

// ── Render ─────────────────────────────────────────────────
function render() {
  const data = getFilteredData();

  $('resultsCount').textContent = `${data.length} opportunit${data.length !== 1 ? 'ies' : 'y'}`;

  if (data.length === 0) {
    grid.innerHTML = '';
    emptyState.hidden = false;
    return;
  }
  emptyState.hidden = true;

  const isArchive = State.activeTab === 'archive';
  grid.innerHTML = data.map((o, i) => buildCard(o, isArchive, i)).join('');

  // Bind card click
  grid.querySelectorAll('.opp-card').forEach(card => {
    card.addEventListener('click', e => {
      if (e.target.closest('.card-apply-btn')) return;
      openModal(card.dataset.id, isArchive);
    });
  });
}

function buildCard(o, isArchive, idx) {
  const today    = new Date();
  const deadline = o.deadline ? new Date(o.deadline) : null;
  const in48h    = new Date(today.getTime() - 48 * 3600000);
  const in7      = new Date(today.getTime() + 7 * 86400000);

  const isNew     = o.date_added && new Date(o.date_added) >= in48h;
  const isClosing = deadline && deadline >= today && deadline <= in7;

  let classes = 'opp-card';
  if (o.region === 'national') classes += ' is-national';
  if (isNew)     classes += ' is-new';
  if (isClosing) classes += ' is-closing';
  if (isArchive) classes += ' is-archived';

  const typeBadge = `<span class="card-type-badge badge-${o.type || 'grant'}">${o.type || 'grant'}</span>`;
  const flag = o.region === 'national' ? '🇵🇰' : '🌍';

  const deadlineLabel = isArchive
    ? `<span class="deadline-badge archived-badge">Closed</span>`
    : deadline
      ? `<span class="deadline-badge">${isClosing ? '⏳ ' : '📅 '}${formatDate(deadline)}${isClosing ? countdownStr(deadline) : ''}</span>`
      : '';

  const prizeLabel = o.prize
    ? `<span class="prize-badge">💰 ${o.prize}</span>`
    : '';

  const applyLink = o.application_link
    ? `<a class="card-apply-btn" href="${escHtml(o.application_link)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Apply ↗</a>`
    : '';

  return `
  <article class="${classes}" data-id="${escHtml(o.id)}" style="animation-delay:${Math.min(idx * 30, 300)}ms">
    <div class="card-header">
      <div>${typeBadge}</div>
      <span class="region-flag" title="${o.region === 'national' ? 'Pakistan' : 'International'}">${flag}</span>
    </div>
    <div>
      <div class="card-title">${escHtml(o.name || 'Untitled')}</div>
      <div class="card-org">${escHtml(o.organization || '')}</div>
    </div>
    <div class="card-meta">${deadlineLabel}${prizeLabel}</div>
    ${o.requirements ? `<p class="card-requirements">${escHtml(o.requirements)}</p>` : ''}
    <div class="card-footer">
      <span class="card-source" title="${escHtml(o.source || '')}">${escHtml(domainFromUrl(o.source))}</span>
      ${applyLink}
    </div>
  </article>`;
}

// ── Modal ──────────────────────────────────────────────────
function openModal(id, isArchive) {
  const pool = isArchive ? State.archive : State.opportunities;
  const o = pool.find(x => x.id === id);
  if (!o) return;

  const deadline = o.deadline ? new Date(o.deadline) : null;
  const today = new Date();
  const in7 = new Date(today.getTime() + 7 * 86400000);
  const isClosing = deadline && deadline >= today && deadline <= in7;

  modalContent.innerHTML = `
    <div class="modal-eyebrow">
      <span class="card-type-badge badge-${o.type || 'grant'}">${o.type || 'grant'}</span>
      <span>${o.region === 'national' ? '🇵🇰 Pakistan' : '🌍 International'}</span>
    </div>
    <h2 class="modal-title">${escHtml(o.name || '')}</h2>
    <p class="modal-org">${escHtml(o.organization || '')}</p>
    ${field('Deadline', deadline ? `${formatDate(deadline)}${isClosing ? ' <span class="countdown-text">— Closing soon!</span>' : ''}` : 'Not specified', true)}
    ${field('Prize / Funding', o.prize || 'Not specified')}
    ${field('Requirements', o.requirements || 'See official page')}
    ${field('Country / Region', `${o.country || ''}${o.country && o.region ? ' · ' : ''}${o.region || ''}`)}
    ${field('Source', o.source ? `<a href="${escHtml(o.source)}" target="_blank" rel="noopener" style="color:var(--accent-3)">${escHtml(o.source)}</a>` : 'N/A', true)}
    ${field('Date Added', o.date_added ? formatDate(new Date(o.date_added)) : 'N/A')}
    ${o.application_link
      ? `<a class="modal-apply-btn" href="${escHtml(o.application_link)}" target="_blank" rel="noopener">Apply Now ↗</a>`
      : '<p style="margin-top:16px;font-size:13px;color:var(--text-muted)">No direct link available. Check official source.</p>'
    }
  `;

  modalOverlay.hidden = false;
  document.body.style.overflow = 'hidden';
}

function field(label, value, raw = false) {
  return `
  <div class="modal-field">
    <div class="modal-field-label">${label}</div>
    <div class="modal-field-value">${raw ? value : escHtml(value)}</div>
  </div>`;
}

$('modalClose').addEventListener('click', closeModal);
modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
function closeModal() {
  modalOverlay.hidden = true;
  document.body.style.overflow = '';
}

// ── Events ─────────────────────────────────────────────────
function bindEvents() {
  // Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      State.activeTab = btn.dataset.tab;
      render();
    });
  });

  // Search
  searchInput.addEventListener('input', e => {
    State.searchQuery = e.target.value;
    searchClear.classList.toggle('visible', e.target.value.length > 0);
    render();
  });
  searchClear.addEventListener('click', () => {
    searchInput.value = '';
    State.searchQuery = '';
    searchClear.classList.remove('visible');
    searchInput.focus();
    render();
  });

  // Sort
  sortSelect.addEventListener('change', e => {
    State.sortBy = e.target.value;
    render();
  });

  // Export
  $('exportBtn').addEventListener('click', exportCSV);
  $('footerExport').addEventListener('click', e => { e.preventDefault(); exportCSV(); });
}

// ── CSV Export ─────────────────────────────────────────────
function exportCSV() {
  const all = [...State.archive, ...State.opportunities.filter(o => o.status === 'Closed')];
  if (all.length === 0) { alert('Archive is empty.'); return; }

  const headers = ['id','name','organization','type','country','region','deadline','prize','requirements','application_link','source','date_added','status'];
  const rows = [headers.join(',')];
  all.forEach(o => {
    rows.push(headers.map(h => `"${(o[h] || '').toString().replace(/"/g, '""')}"`).join(','));
  });
  const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `cmaced-archive-${new Date().getFullYear()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── Helpers ────────────────────────────────────────────────
function escHtml(str) {
  return String(str || '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}
function formatDate(d) {
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}
function countdownStr(deadline) {
  const diff = Math.ceil((deadline - new Date()) / 86400000);
  return diff <= 0 ? '' : ` · ${diff}d left`;
}
function domainFromUrl(url) {
  try { return new URL(url).hostname.replace('www.',''); } catch { return url || ''; }
}

// ── Sample Data (fallback) ─────────────────────────────────
function getSampleData() {
  const today = new Date();
  const d = (n) => {
    const dd = new Date(today.getTime() + n * 86400000);
    return dd.toISOString().split('T')[0];
  };
  return [
    {
      id: 'ignite-startup-fund-2025',
      name: 'Ignite Startup Fund',
      organization: 'Ignite National Technology Fund',
      type: 'grant',
      country: 'Pakistan',
      region: 'national',
      deadline: d(45),
      prize: 'PKR 5–25 million',
      requirements: 'Early-stage tech startups registered in Pakistan. Must have working prototype.',
      application_link: 'https://ignite.org.pk/programs/',
      source: 'https://ignite.org.pk',
      date_added: d(-1),
      status: 'Open'
    },
    {
      id: 'plan9-cohort-2025',
      name: 'Plan9 Incubation Program',
      organization: 'PITB – Punjab Information Technology Board',
      type: 'accelerator',
      country: 'Pakistan',
      region: 'national',
      deadline: d(30),
      prize: 'Office space + PKR 1M seed',
      requirements: 'Tech-based startup teams from Punjab. Pre-revenue or early revenue stage.',
      application_link: 'https://plan9.pitb.gov.pk',
      source: 'https://plan9.pitb.gov.pk',
      date_added: d(-2),
      status: 'Open'
    },
    {
      id: 'nic-lahore-2025',
      name: 'National Incubation Center Lahore',
      organization: 'NIC Lahore / STZA',
      type: 'accelerator',
      country: 'Pakistan',
      region: 'national',
      deadline: d(20),
      prize: 'USD 10,000 + mentorship',
      requirements: 'Pakistani founders, tech/innovation focused, must present to panel.',
      application_link: 'https://niclahore.com',
      source: 'https://niclahore.com',
      date_added: d(-3),
      status: 'Open'
    },
    {
      id: 'yc-w2025',
      name: 'Y Combinator Winter 2026',
      organization: 'Y Combinator',
      type: 'accelerator',
      country: 'USA',
      region: 'international',
      deadline: d(60),
      prize: 'USD 500,000',
      requirements: 'Any stage, any country. Online application. Equity-based.',
      application_link: 'https://www.ycombinator.com/apply',
      source: 'https://www.ycombinator.com',
      date_added: d(-1),
      status: 'Open'
    },
    {
      id: 'hult-prize-2025',
      name: 'Hult Prize 2025–26',
      organization: 'Hult Prize Foundation',
      type: 'competition',
      country: 'Global',
      region: 'international',
      deadline: d(14),
      prize: 'USD 1,000,000',
      requirements: 'University student teams. Social impact focus. Virtual application open.',
      application_link: 'https://www.hultprize.org',
      source: 'https://www.hultprize.org',
      date_added: d(-0),
      status: 'Open'
    },
    {
      id: 'mit-solve-2025',
      name: 'MIT Solve Global Challenge',
      organization: 'MIT Solve',
      type: 'competition',
      country: 'Global',
      region: 'international',
      deadline: d(90),
      prize: 'USD 10,000–150,000',
      requirements: 'Social entrepreneurs worldwide. Online application accepted from Pakistan.',
      application_link: 'https://solve.mit.edu',
      source: 'https://solve.mit.edu',
      date_added: d(-4),
      status: 'Open'
    },
    {
      id: 'google-startup-fund-2025',
      name: 'Google for Startups Accelerator',
      organization: 'Google',
      type: 'accelerator',
      country: 'Global',
      region: 'international',
      deadline: d(50),
      prize: 'USD 100,000 in Cloud credits + equity-free',
      requirements: 'Series A or earlier. AI/ML focused preferred. Virtual participation available.',
      application_link: 'https://startup.google.com/programs/accelerator/',
      source: 'https://startup.google.com',
      date_added: d(-2),
      status: 'Open'
    },
    {
      id: 'msft-founders-hub-2025',
      name: 'Microsoft for Startups Founders Hub',
      organization: 'Microsoft',
      type: 'grant',
      country: 'Global',
      region: 'international',
      deadline: d(365),
      prize: 'USD 150,000 in Azure credits',
      requirements: 'Pre-seed to Series A. No equity required. Open to Pakistan-based startups.',
      application_link: 'https://www.microsoft.com/en-us/startups',
      source: 'https://www.microsoft.com/en-us/startups',
      date_added: d(-5),
      status: 'Open'
    },
    {
      id: 'seedstars-pakistan-2025',
      name: 'Seedstars Pakistan',
      organization: 'Seedstars World',
      type: 'competition',
      country: 'Pakistan',
      region: 'national',
      deadline: d(25),
      prize: 'USD 500,000 investment',
      requirements: 'Early-stage tech startups. Local qualifying round then global finals.',
      application_link: 'https://www.seedstars.com/programs/',
      source: 'https://www.seedstars.com',
      date_added: d(-2),
      status: 'Open'
    },
    {
      id: 'hec-innovation-2025',
      name: 'HEC Innovation Fund',
      organization: 'Higher Education Commission Pakistan',
      type: 'grant',
      country: 'Pakistan',
      region: 'national',
      deadline: d(35),
      prize: 'PKR 2–10 million',
      requirements: 'University-affiliated researchers and student entrepreneurs.',
      application_link: 'https://hec.gov.pk/english/services/faculty/NRPU/Pages/Default.aspx',
      source: 'https://hec.gov.pk',
      date_added: d(-6),
      status: 'Open'
    },
    {
      id: 'un-sdg-2025',
      name: 'UN SDG Innovation Fund',
      organization: 'United Nations',
      type: 'fellowship',
      country: 'Global',
      region: 'international',
      deadline: d(75),
      prize: 'USD 50,000–300,000',
      requirements: 'Social ventures aligned with UN SDGs. Virtual application from any country.',
      application_link: 'https://www.un.org/en/academic-impact/entrepreneurship',
      source: 'https://www.un.org',
      date_added: d(-3),
      status: 'Open'
    },
    {
      id: 'cmaced-startup-grant-2025',
      name: 'CMACED Internal Startup Grant',
      organization: 'CMACED – Superior University',
      type: 'grant',
      country: 'Pakistan',
      region: 'national',
      deadline: d(10),
      prize: 'PKR 500,000',
      requirements: 'Currently enrolled Superior University students. Prototype required.',
      application_link: 'https://cmaced.superior.edu.pk',
      source: 'https://superior.edu.pk',
      date_added: d(0),
      status: 'Open'
    },
    {
      id: 'lums-entrepreneurship-2025',
      name: 'LUMS Centre for Entrepreneurship Program',
      organization: 'LUMS – Lahore University of Management Sciences',
      type: 'accelerator',
      country: 'Pakistan',
      region: 'national',
      deadline: d(40),
      prize: 'Mentorship + USD 5,000 seed',
      requirements: 'Open to all Pakistani university graduates and students.',
      application_link: 'https://lums.edu.pk/centre-entrepreneurship',
      source: 'https://lums.edu.pk',
      date_added: d(-7),
      status: 'Open'
    },
    {
      id: 'masschallenge-2025',
      name: 'MassChallenge Global Program',
      organization: 'MassChallenge',
      type: 'accelerator',
      country: 'Global',
      region: 'international',
      deadline: d(55),
      prize: 'USD 250,000 equity-free',
      requirements: 'No equity taken. Open to international founders including Pakistan.',
      application_link: 'https://masschallenge.org',
      source: 'https://masschallenge.org',
      date_added: d(-4),
      status: 'Open'
    },
    {
      id: 'pseb-ites-2025',
      name: 'PSEB IT Export Startup Support',
      organization: 'Pakistan Software Export Board',
      type: 'grant',
      country: 'Pakistan',
      region: 'national',
      deadline: d(18),
      prize: 'PKR 3 million + export facilitation',
      requirements: 'IT/software companies targeting export markets. Must be PSEB registered.',
      application_link: 'https://pseb.org.pk/startups',
      source: 'https://pseb.org.pk',
      date_added: d(-5),
      status: 'Open'
    },
    {
      id: 'devpost-global-hack-2025',
      name: 'Global AI Hackathon – Devpost',
      organization: 'Devpost',
      type: 'hackathon',
      country: 'Global',
      region: 'international',
      deadline: d(7),
      prize: 'USD 50,000',
      requirements: 'Virtual. Open to all nationalities. Individual or team submission.',
      application_link: 'https://devpost.com/hackathons',
      source: 'https://devpost.com',
      date_added: d(-1),
      status: 'Open'
    }
  ];
}
