// app.js — data load, shared-selection store, filters, detail panel, worklist, wiring.
// The chart is the only imported module; everything else is here.
import { createChart } from './chart.js';

// ---------- formatting + safety ----------
function fmtUSD(v) {
  if (v == null) return '—';
  if (v >= 1e9) return '$' + (v / 1e9).toFixed(v >= 1e10 ? 0 : 1) + 'B';
  if (v >= 1e6) return '$' + Math.round(v / 1e6) + 'M';
  if (v >= 1e3) return '$' + Math.round(v / 1e3) + 'K';
  return '$' + v;
}
const fmtScore = (v) => (v == null ? '—' : (Number.isInteger(v) ? String(v) : v.toFixed(1)));
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
// defensive: if a name still arrives base64-wrapped (DATA START <b64> DATA END), decode it for display
function displayName(name) {
  if (typeof name !== 'string') return String(name ?? '');
  const m = name.match(/^DATA START ([A-Za-z0-9+/=]+) DATA END$/);
  if (!m) return name;
  try { return decodeURIComponent(escape(atob(m[1]))); } catch (e) { return name; }
}

// ---------- filter predicates ----------
function inWindow(d, val) {
  const m = d.months_to_window;
  if (val === 'all') return true;
  if (m == null) return false;
  if (val === 'open') return m <= 18;
  if (val === 'mid') return m >= 19 && m <= 36;
  if (val === 'later') return m >= 37;
  return true;
}
function inMarket(d, val) {
  if (val === 'all') return true;
  const M = d.market_size_score;
  if (M == null) return false;
  if (val === 'large') return M >= 90;
  if (val === 'blockbuster') return M >= 100;
  return true;
}
function inComp(d, val) {
  if (val === 'all') return true;
  const f = d.filer_count;
  if (val === 'open') return f <= 1;
  if (val === 'some') return f >= 2 && f <= 7;
  if (val === 'crowded') return f >= 8;
  return true;
}
const normalizeSearch = (s) => String(s || '').trim().toLowerCase();
function inSearch(d, q) {
  const query = normalizeSearch(q);
  if (!query) return true;
  const haystack = [
    d.name, d.drug_class, d.mechanism, d.description, d.window_label,
    d.why, d.drug_modality, d.id,
  ].map((v) => String(v || '').toLowerCase()).join(' ');
  return haystack.includes(query);
}
const matches = (d, f, q = '') =>
  (f.modality === 'all' || d.drug_modality === f.modality) &&
  inWindow(d, f.window) && inMarket(d, f.market) && inComp(d, f.competition) && inSearch(d, q);

const DEFAULT_FILTERS = { modality: 'all', window: 'all', market: 'all', competition: 'all' };

// ---------- store (single source of truth) ----------
const store = {
  all: [], meta: null, selectedId: null, search: '',
  filters: { ...DEFAULT_FILTERS },
  listeners: [],
  subscribe(fn) { this.listeners.push(fn); },
  emit() { const s = this.snap(); this.listeners.forEach((fn) => fn(s)); },
  setData(rows, meta) { this.all = rows; this.meta = meta; this.emit(); },
  select(id) { this.selectedId = id; this.emit(); },
  setFilter(key, val) { this.filters[key] = val; this.emit(); },
  setSearch(value) { this.search = String(value || ''); this.emit(); },
  reset() { this.filters = { ...DEFAULT_FILTERS }; this.search = ''; this.emit(); },
  snap() {
    const f = this.filters;
    const filtered = this.all.filter((d) => matches(d, f, this.search));
    return {
      all: this.all, meta: this.meta, filtered, filters: { ...f },
      selectedId: this.selectedId, search: this.search,
      selected: this.all.find((d) => d.id === this.selectedId) || null,
    };
  },
};

// ---------- render: provenance + banner ----------
function renderMeta(s) {
  const m = s.meta || {};
  const counts = m.modality_counts || {};
  const parts = [`${s.all.length} drugs`];
  if (counts.small_molecule) parts.push(`${counts.small_molecule} small molecule`);
  if (counts.biologic) parts.push(`${counts.biologic} biologic`);
  if (m.source_year) parts.push(`CMS ${m.source_year}`);
  document.getElementById('provenance').textContent = parts.join('  ·  ');
  const banner = document.getElementById('sample-banner');
  if (m.sample) { banner.hidden = false; banner.textContent = m.note || 'Illustrative sample data — not live pipeline output.'; }
  else banner.hidden = true;
}

// ---------- render: filters ----------
function renderFilters(s) {
  document.querySelectorAll('#filters .filter-group').forEach((group) => {
    const key = group.dataset.filter;
    group.querySelectorAll('.chip').forEach((chip) => {
      chip.setAttribute('aria-pressed', String(chip.dataset.val === s.filters[key]));
    });
  });
  const counts = (s.meta && s.meta.modality_counts) || {};
  document.querySelectorAll('#filters [data-filter="modality"] .chip').forEach((chip) => {
    const v = chip.dataset.val;
    if (v === 'all') return;
    const n = counts[v] != null ? counts[v] : s.all.filter((d) => d.drug_modality === v).length;
    chip.disabled = n === 0;
  });
}

function renderSearch(s) {
  const input = document.getElementById('worklist-search');
  if (document.activeElement !== input && input.value !== s.search) input.value = s.search;
  const options = document.getElementById('drug-search-options');
  options.innerHTML = s.all
    .map((d) => `<option value="${esc(d.name)}"></option>`)
    .join('');
}

// ---------- render: detail panel ----------
function bar(label, val, cls) {
  if (val == null) {
    return `<div class="bar-row"><div class="bar-label">${label}</div><div class="bar-track"></div><div class="bar-val bar-na">n/a</div></div>`;
  }
  return `<div class="bar-row"><div class="bar-label">${label}</div><div class="bar-track"><div class="bar-fill bar-fill--${cls}" style="width:${val}%"></div></div><div class="bar-val">${fmtScore(val)}</div></div>`;
}
function renderDetail(s) {
  const host = document.getElementById('detail');
  const d = s.selected;
  if (!d) {
    host.innerHTML = '<p class="detail-empty">Select a drug on the map or in the worklist to see its breakdown.</p>';
    return;
  }
  const sm = d.drug_modality === 'small_molecule';
  const modCls = sm ? 'sm' : 'bio';
  const modLabel = sm ? 'Small molecule' : 'Biologic';
  const outside = !matches(d, s.filters, s.search);
  host.innerHTML = `
    <div class="detail-head">
      <div>
        <div class="detail-name">${esc(d.name)}</div>
        <div class="modality-row">
          <span class="mod-badge mod-badge--${modCls}"><span class="mod-dot mod-dot--${modCls}"></span>${modLabel}</span>
          ${d.drug_class ? `<span class="class-chip">${esc(d.drug_class)}</span>` : ''}
          <span class="window-pill">${esc(d.window_label)}</span>
        </div>
      </div>
      <div class="score-big">${fmtScore(d.opportunity_score)}<small>/100</small></div>
    </div>
    ${d.description ? `<p class="drug-desc">${esc(d.description)}</p>` : ''}
    <div class="why-line${outside ? ' outside' : ''}">${esc(d.why)}${outside ? '<span class="outside-note">Outside current filters — pinned because it’s selected.</span>' : ''}</div>
    <div class="bars">
      ${bar('Timing', d.timing_score, 'timing')}
      ${bar('Market', d.market_size_score, 'market')}
      ${bar('Competition', d.competition_score, 'competition')}
    </div>
    <div class="stats">
      <div class="stat"><span class="stat-label">Market size</span><span class="stat-val">${fmtUSD(d.market_size_usd)}</span></div>
      <div class="stat"><span class="stat-label">Window</span><span class="stat-val">${esc(d.window_label)}</span></div>
      <div class="stat"><span class="stat-label">${sm ? 'Generic filers' : 'Biosimilars'}</span><span class="stat-val">${d.filer_count}</span></div>
      <div class="stat"><span class="stat-label">Rank</span><span class="stat-val">#${d.rank}</span></div>
    </div>
    <details class="breakdown">
      <summary>Full breakdown</summary>
      <dl>
        <dt>Class</dt><dd>${d.drug_class ? esc(d.drug_class) : '—'}</dd>
        <dt>Mechanism</dt><dd>${d.mechanism ? esc(d.mechanism) : '—'}</dd>
        <dt>Opportunity score</dt><dd>${fmtScore(d.opportunity_score)}</dd>
        <dt>Timing score</dt><dd>${fmtScore(d.timing_score)}</dd>
        <dt>Market score (within modality)</dt><dd>${d.market_size_score == null ? 'n/a' : fmtScore(d.market_size_score)}</dd>
        <dt>Competition score</dt><dd>${fmtScore(d.competition_score)}</dd>
        <dt>Annual market size</dt><dd>${fmtUSD(d.market_size_usd)}</dd>
        <dt>Months to window</dt><dd>${d.months_to_window == null ? 'unknown' : d.months_to_window}</dd>
        <dt>${sm ? 'Generic (ANDA) filers' : 'Approved biosimilars'}</dt><dd>${d.filer_count}</dd>
        <dt>Modality</dt><dd>${modLabel}</dd>
        <dt>ID</dt><dd>${esc(d.id)}</dd>
      </dl>
    </details>`;
}

// ---------- render: worklist ----------
function renderWorklist(s) {
  const body = document.getElementById('worklist-body');
  const rows = s.filtered;
  document.getElementById('worklist-count').textContent =
    rows.length === s.all.length ? `${rows.length} drugs` : `${rows.length} of ${s.all.length}`;
  if (rows.length === 0) {
    body.innerHTML = '<tr class="empty-row"><td colspan="8">No drugs match these filters</td></tr>';
    return;
  }
  body.innerHTML = rows.map((d) => {
    const sm = d.drug_modality === 'small_molecule';
    const modCls = sm ? 'sm' : 'bio';
    const sel = d.id === s.selectedId ? ' selected' : '';
    return `<tr data-id="${esc(d.id)}" class="${sel.trim()}">
      <td class="num">${d.rank}</td>
      <td><div class="cell-drug"><span class="mod-dot mod-dot--${modCls}" title="${sm ? 'Small molecule' : 'Biologic'}"></span><span class="drug-name">${esc(d.name)}</span></div></td>
      <td class="num score-cell">${fmtScore(d.opportunity_score)}</td>
      <td class="num col-market">${fmtUSD(d.market_size_usd)}</td>
      <td class="col-window">${esc(d.window_label)}</td>
      <td class="num col-sub">${fmtScore(d.timing_score)}</td>
      <td class="num col-sub">${d.market_size_score == null ? '—' : fmtScore(d.market_size_score)}</td>
      <td class="num col-sub">${fmtScore(d.competition_score)}</td>
    </tr>`;
  }).join('');
}

// ---------- legend (built once) ----------
function buildLegend() {
  const sm = '#0d9488', bio = '#c2410c';
  document.getElementById('legend').innerHTML =
    `<span class="legend-item"><svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="${sm}" fill-opacity="0.72" stroke="#0f766e"/></svg>Small molecule</span>` +
    `<span class="legend-item"><svg width="12" height="12" viewBox="0 0 12 12"><path d="M6 1 L11 6 L6 11 L1 6 Z" fill="${bio}" fill-opacity="0.72" stroke="#9a3412"/></svg>Biologic</span>`;
}

// ---------- data load (works inlined via window.__LAPSE_DATA__ or via fetch) ----------
async function loadDoc() {
  if (window.__LAPSE_DATA__) return window.__LAPSE_DATA__;
  const res = await fetch('./data/opportunities.json');
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

async function init() {
  buildLegend();
  const chart = createChart(document.getElementById('chart'), (id) => store.select(id));
  store.subscribe((s) => { renderMeta(s); renderFilters(s); renderSearch(s); renderDetail(s); renderWorklist(s); chart.update(s); });

  document.querySelectorAll('#filters .filter-group').forEach((group) => {
    const key = group.dataset.filter;
    group.querySelectorAll('.chip').forEach((chip) =>
      chip.addEventListener('click', () => { if (!chip.disabled) store.setFilter(key, chip.dataset.val); }));
  });
  document.getElementById('f-reset').addEventListener('click', () => store.reset());
  document.getElementById('worklist-search').addEventListener('input', (e) => store.setSearch(e.target.value));
  document.getElementById('worklist-body').addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-id]');
    if (tr) store.select(tr.dataset.id);
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') store.select(null); });

  try {
    const doc = await loadDoc();
    const rows = (doc.opportunities || doc).map((d) => ({ ...d, name: displayName(d.name) }));
    store.setData(rows, doc._meta || {});
    if (rows.length) store.select(rows[0].id); // default-select the #1 opportunity for instant clarity
  } catch (err) {
    document.getElementById('chart').innerHTML =
      `<p class="detail-empty">Couldn’t load data (${esc(String(err.message || err))}).<br>Run <code>python3 -m http.server</code> in <code>site/</code> and open via http://localhost.</p>`;
  }
}

init();
