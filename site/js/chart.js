// chart.js — the opportunity map. Hand-rolled inline SVG, zero dependencies.
// Tufte treatment: log-$ y, linear-months x, area-proportional bubbles, redundant
// colour+shape per modality, a sweet-spot region tied to the scoring thresholds,
// range-frame axes, a right label strip with de-collision. Responsive via ResizeObserver.

const NS = 'http://www.w3.org/2000/svg';
const Y_DOMAIN = [1e6, 5e10];        // $1M … $50B (headroom above the biggest biologic)
const SWEET_X = [1, 18];             // months where timing_score == 100
const SWEET_FLOOR = 5e8;             // $500M — where market_size_score >= 90
const X_TICKS = [-60, -36, -18, 0, 18, 36, 60];

function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) {
    if (k === 'text') e.textContent = attrs[k];
    else if (k === 'style') e.setAttribute('style', attrs[k]);
    else e.setAttribute(k, attrs[k]);
  }
  if (parent) parent.appendChild(e);
  return e;
}
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
function hash(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
function usdShort(v) {
  if (v == null) return 'n/a';
  if (v >= 1e9) return '$' + (v / 1e9).toFixed(v >= 1e10 ? 0 : 1) + 'B';
  if (v >= 1e6) return '$' + Math.round(v / 1e6) + 'M';
  return '$' + Math.round(v / 1e3) + 'K';
}
const fmtScore = (v) => (v == null ? '—' : (Number.isInteger(v) ? String(v) : v.toFixed(1)));

export function createChart(container, onSelect) {
  let state = null;
  const svg = el('svg', { preserveAspectRatio: 'xMidYMid meet' });
  container.appendChild(svg);
  const ro = new ResizeObserver(() => { if (state) render(); });
  ro.observe(container);

  function render() {
    const W = container.clientWidth;
    const H = container.clientHeight;
    if (!W || !H) return;
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);

    const data = state.all;
    const filteredIds = new Set(state.filtered.map((d) => d.id));
    const selectedId = state.selectedId;
    const filtersActive = state.filtered.length !== data.length;

    const labelStrip = W >= 720;
    const margin = { top: 26, right: labelStrip ? 140 : 16, bottom: 44, left: 60 };
    const hasNull = data.some((d) => d.market_size_usd == null);
    const laneH = hasNull ? 22 : 0;
    const plotLeft = margin.left;
    const plotRight = W - margin.right;
    const plotTop = margin.top;
    const baseline = H - margin.bottom;
    const plotBottom = baseline - laneH;
    const laneY = (plotBottom + baseline) / 2;

    const months = data.map((d) => d.months_to_window).filter((v) => v != null);
    const xMin = Math.min(-66, ...months);
    const xMax = Math.max(66, ...months);
    const xs = (v) => plotLeft + ((v - xMin) / (xMax - xMin)) * (plotRight - plotLeft);
    const yLo = Math.log10(Y_DOMAIN[0]);
    const yHi = Math.log10(Y_DOMAIN[1]);
    const ys = (v) => plotBottom - ((Math.log10(v) - yLo) / (yHi - yLo)) * (plotBottom - plotTop);
    const rMin = W < 520 ? 3 : 4;
    const rMax = W < 520 ? 15 : 22;          // smaller bubbles on narrow screens to cut overlap
    const rs = (score) => rMin + (rMax - rMin) * Math.sqrt(Math.max(0, score) / 100);
    const jit = (id) => { const h = hash(id); return { dx: ((h & 255) / 255 - 0.5) * 7, dy: (((h >> 8) & 255) / 255 - 0.5) * 7 }; };

    // ---------- layer 1: sweet-spot region (recedes, painted first) ----------
    const sweetX0 = clamp(xs(SWEET_X[0]), plotLeft, plotRight);
    const sweetX1 = clamp(xs(SWEET_X[1]), plotLeft, plotRight);
    const sweetTop = plotTop;
    const sweetBot = clamp(ys(SWEET_FLOOR), plotTop, plotBottom);
    el('rect', { class: 'sweet-fill', x: sweetX0, y: sweetTop, width: Math.max(0, sweetX1 - sweetX0), height: Math.max(0, sweetBot - sweetTop) }, svg);
    // softer extension over the just-expired band [-12, 0]
    const ext0 = clamp(xs(-12), plotLeft, plotRight);
    const ext1 = sweetX0;
    el('rect', { class: 'sweet-fill--soft', x: ext0, y: sweetTop, width: Math.max(0, ext1 - ext0), height: Math.max(0, sweetBot - sweetTop) }, svg);
    // sweet-spot label in the top margin (collision-safe strip above the plot)
    el('circle', { cx: sweetX0 + 7, cy: plotTop - 9, r: 4, style: 'fill:var(--accent)' }, svg);
    el('text', { class: 'sweet-label', x: sweetX0 + 16, y: plotTop - 5, text: 'sweet spot · near-term + ≥$500M' }, svg);

    // ---------- layer 2: market thresholds ($500M, $1B) ----------
    [SWEET_FLOOR, 1e9].forEach((v) => {
      el('line', { class: 'threshold-line', x1: plotLeft, x2: plotRight, y1: ys(v), y2: ys(v) }, svg);
    });

    // ---------- layer 3: axes (range-frame) + now line ----------
    el('line', { class: 'axis-line', x1: xs(Math.max(xMin, Math.min(...months))), x2: xs(Math.min(xMax, Math.max(...months))), y1: baseline, y2: baseline }, svg);
    // now line
    const nowX = xs(0);
    el('line', { class: 'now-line', x1: nowX, x2: nowX, y1: plotTop, y2: baseline }, svg);
    el('text', { class: 'now-label', x: nowX, y: baseline + 14, 'text-anchor': 'middle', text: 'now' }, svg);
    // x ticks
    X_TICKS.filter((v) => v >= xMin && v <= xMax && v !== 0).forEach((v) => {
      const tx = xs(v);
      el('line', { class: 'axis-line', x1: tx, x2: tx, y1: baseline, y2: baseline + 4 }, svg);
      el('text', { class: 'tick-label', x: tx, y: baseline + 14, 'text-anchor': 'middle', text: String(v) }, svg);
    });
    // x direction captions
    el('text', { class: 'band-caption', x: plotLeft, y: baseline + 30, 'text-anchor': 'start', text: '◀ window already open' }, svg);
    el('text', { class: 'band-caption', x: plotRight, y: baseline + 30, 'text-anchor': 'end', text: 'months until expiry ▶' }, svg);
    // y ticks (decade) — labels in the left margin, no gridlines
    [1e7, 1e8, 1e9, 1e10].forEach((v) => {
      const ty = ys(v);
      el('text', { class: 'tick-label', x: plotLeft - 8, y: ty + 4, 'text-anchor': 'end', text: usdShort(v) }, svg);
    });
    el('text', { class: 'axis-title', x: plotLeft - 8, y: plotTop - 12, 'text-anchor': 'end', text: 'market' }, svg);

    // ---------- unknown-market lane ----------
    if (hasNull) {
      el('line', { class: 'threshold-line', x1: plotLeft, x2: plotRight, y1: plotBottom, y2: plotBottom }, svg);
      el('text', { class: 'gutter-label', x: plotLeft - 8, y: laneY + 4, 'text-anchor': 'end', text: 'unknown' }, svg);
    }

    // ---------- compute positions ----------
    const pts = data.map((d) => {
      const j = jit(d.id);
      const nullM = d.market_size_usd == null;
      const nullX = d.months_to_window == null;
      const cx = nullX ? plotLeft + 6 : clamp(xs(d.months_to_window) + j.dx, plotLeft, plotRight);
      const cy = nullM ? laneY : clamp(ys(d.market_size_usd) + j.dy, plotTop, plotBottom);
      const dim = filtersActive && !filteredIds.has(d.id) && d.id !== selectedId;
      return { d, cx, cy, r: rs(d.opportunity_score), nullM, nullX, dim, selected: d.id === selectedId };
    });

    // ---------- layer 4: bubbles (dim → active largest-first → selected on top) ----------
    pts.filter((p) => p.dim).forEach((p) => drawBubble(svg, p, 'dim', onSelect));
    pts.filter((p) => !p.dim && !p.selected).sort((a, b) => b.d.opportunity_score - a.d.opportunity_score)
      .forEach((p) => drawBubble(svg, p, 'active', onSelect));
    const selPt = pts.find((p) => p.selected);
    if (selPt) drawBubble(svg, selPt, 'selected', onSelect);

    // empty state
    if (filtersActive && state.filtered.length === 0) {
      el('text', { class: 'empty-msg', x: (plotLeft + plotRight) / 2, y: (plotTop + plotBottom) / 2, 'text-anchor': 'middle', text: 'No drugs match these filters' }, svg);
    }

    // ---------- layer 5: direct labels (top-5 + selected) in the right strip ----------
    if (labelStrip) {
      const candidates = pts.filter((p) => !p.dim);
      let labels = candidates.slice().sort((a, b) => b.d.opportunity_score - a.d.opportunity_score).slice(0, 5);
      if (selPt && !labels.includes(selPt)) labels.push(selPt);
      labels.sort((a, b) => a.cy - b.cy);
      const gap = 30; let prev = plotTop - gap;
      labels.forEach((L) => { L.ly = clamp(Math.max(L.cy, prev + gap), plotTop + 4, baseline - 4); prev = L.ly; });
      const labelX = plotRight + 10;
      labels.forEach((L) => {
        const accent = L.selected;
        el('path', { class: 'leader', d: `M ${L.cx} ${L.cy} L ${labelX - 5} ${L.ly}`, style: accent ? 'stroke:var(--accent)' : '' }, svg);
        el('text', { class: 'dlabel-name', x: labelX, y: L.ly - 2, text: L.d.name, style: accent ? 'fill:var(--accent)' : '' }, svg);
        el('text', { class: 'dlabel-meta', x: labelX, y: L.ly + 11, text: `${fmtScore(L.d.opportunity_score)} · ${usdShort(L.d.market_size_usd)}` }, svg);
      });
    }
  }

  function update(s) { state = s; render(); }
  return { update };
}

function drawBubble(svg, p, mode, onSelect) {
  const d = p.d;
  const sm = d.drug_modality === 'small_molecule';
  const g = el('g', { class: 'bubble' }, svg);

  // invisible hit target (>=24px tap area) — sits behind the visible mark
  el('circle', { cx: p.cx, cy: p.cy, r: Math.max(p.r, 13), style: 'fill:transparent' }, g);

  // visible mark
  let mark;
  if (sm) {
    mark = el('circle', { cx: p.cx, cy: p.cy, r: p.r, class: 'mark' }, g);
  } else {
    const dd = p.r * 1.2533; // equal-area diamond
    mark = el('path', { class: 'mark', d: `M ${p.cx} ${p.cy - dd} L ${p.cx + dd} ${p.cy} L ${p.cx} ${p.cy + dd} L ${p.cx - dd} ${p.cy} Z` }, g);
  }
  const color = sm ? 'var(--sm)' : 'var(--bio)';
  const ink = sm ? 'var(--sm-ink)' : 'var(--bio-ink)';
  if (mode === 'dim') {
    mark.style.fill = 'rgba(24,24,27,0.06)';
    mark.style.stroke = 'none';
    g.style.pointerEvents = 'none';
  } else {
    mark.style.fill = color;
    mark.style.fillOpacity = mode === 'selected' ? '1' : '0.72';
    mark.style.stroke = mode === 'selected' ? 'var(--accent)' : ink;
    mark.style.strokeWidth = mode === 'selected' ? '2.2' : '1';
    if (p.nullM) mark.style.strokeDasharray = '2 2';
  }

  if (mode !== 'dim') {
    el('title', { text: `${d.name} — score ${fmtScore(d.opportunity_score)} · ${usdShort(d.market_size_usd)} · ${d.window_label}` }, g);
    g.setAttribute('role', 'button');
    g.setAttribute('tabindex', '0');
    g.setAttribute('aria-label', `${d.name}, ${d.drug_modality.replace('_', ' ')}, score ${fmtScore(d.opportunity_score)}`);
    g.addEventListener('click', () => onSelect(d.id));
    g.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(d.id); } });
  }
}
