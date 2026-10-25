// Application layer: DOM rendering, canvas map, and user interaction.
// Imports the data layer (api.js-equivalent: data.js) for all backend
// communication and the i18n layer for all display text — this file itself
// contains no fetch URLs and no hardcoded user-facing copy.
import { t, tf, bt, getLang, setLang, applyI18n } from './i18n.js';
import { queryString, fetchAnalysis, fetchValidation, fetchTradingPlan, fetchEventStudy, loadImage, exportUrls } from './data.js';

const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = x => x === null ? '—' : (x * 100).toFixed(1) + ' %';

let data = null, images = {}, mode = 'event', revealed = false, selected = null;
let zoom = 1, pan = { x: 0, y: 0 }, fit = 1, base = { x: 0, y: 0 }, drag = null, timer, loadVersion = 0;

const canvas = $('map'), ctx = canvas.getContext('2d');

function params(){
  return { threshold: $('threshold').value, delta: $('delta').value, radius: $('radius').value };
}

function showError(e){
  const msg = e.message || String(e);
  const m = /^img_load_fail:(.+)$/.exec(msg);
  $('error').textContent = m ? t('img_load_fail') + m[1] : bt(msg);
  $('error').style.display = 'block';
  $('status').textContent = t('err_generic');
}

async function load(){
  const version = ++loadVersion;
  $('status').textContent = t('status_computing');
  $('error').style.display = 'none';
  try{
    const q = queryString(params());
    const d = await fetchAnalysis(q);
    let kinds = ['before','event','flood','unknown','forecast','probability','uncertainty','legacy'];
    if (revealed) kinds.push('future','error');
    const ims = await Promise.all(kinds.map(k => loadImage(k, q)));
    if (version !== loadVersion) return;
    data = d;
    images = Object.fromEntries(kinds.map((k,i) => [k, ims[i]]));
    renderStats();
    renderTable();
    renderProvenance();
    renderModelInfo();
    if (selected) focus(selected, false);
    const urls = exportUrls(q);
    $('csv').href = urls.csv;
    $('json').href = urls.json;
    resize();
    setMode(mode);
    $('status').textContent = tf('status_computed', { n: d.sites.length });
    await loadPlan();
    if (revealed) await evaluate();
  }catch(e){
    if (version === loadVersion) showError(e);
  }
}

function renderModelInfo(){
  const m = data.model_info, ct = m.classifier_test;
  const p = x => (x * 100).toFixed(1) + ' %';
  const locale = getLang() === 'de' ? 'de-DE' : 'en-US';
  const gate = m.forecast_release_gate?.passed;
  $('modelproof').innerHTML = `
    <div class="evidence-row">
      <div class="evidence-item"><div class="e-label">${t('model_classifier_label')}</div><div class="e-value accent tabular">${p(ct.learned.f1)}</div></div>
      <div class="evidence-item"><div class="e-label">${t('model_oldrule_label')}</div><div class="e-value tabular">${p(ct.mndwi_fixed_015.f1)}</div></div>
      <div class="evidence-item"><div class="e-label">${t('model_tuned_label')}</div><div class="e-value tabular">${p(ct.mndwi_validation_tuned.f1)}</div></div>
      <div class="evidence-item"><div class="e-label">${t('model_refchips_label')}</div><div class="e-value tabular" style="font-size:17px">${m.reference_chips} / ${m.reference_pixels.toLocaleString(locale)}</div></div>
    </div>
    <p class="hint-text" style="margin-top:14px">${tf('model_hint', { events: esc(m.test_events.join(', ')), hist: m.history_dates.length, pairs: m.forecast_training_pairs })}</p>
    <div class="gate ${gate ? 'pass' : 'fail'}">${gate ? t('model_gate_passed') : t('model_gate_failed')}</div>`;
  $('heroEvidence').innerHTML = tf('hero_evidence', {
    f1: p(ct.learned.f1).trim(),
    base: p(ct.mndwi_fixed_015.f1).trim(),
    gate: `<span class="gate-flag ${gate ? 'pass' : ''}">${gate ? t('hero_gate_pass') : t('hero_gate_fail')}</span>`,
  });
}

function renderStats(){
  const s = data.summary;
  $('area').textContent = s.new_water_km2.toFixed(1) + ' km²';
  $('direct').textContent = s.direct;
  $('indirect').textContent = s.indirect;
  $('coverage').textContent = s.valid_percent + ' %';
  $('sitecount').textContent = tf('sitecount_label', { n: s.sites });
}

function renderTable(){
  const query = ($('site-search').value || '').toLocaleLowerCase();
  $('rows').innerHTML = data.sites
    .filter(s => s.name.toLocaleLowerCase().includes(query))
    .map(s => `<tr data-id="${esc(s.id)}" class="${s.id === selected ? 'selected' : ''}">
      <td class="name"><b>${esc(s.name)}</b><div class="site-signal">${esc(bt(s.signal))}${s.approximate ? t('site_approx_suffix') : ''}</div></td>
      <td class="num tabular">${pct(s.direct_fraction)}</td>
      <td class="num tabular">${pct(s.forecast_fraction)}</td>
      <td class="num tabular">${pct(s.road_fraction)}</td>
      <td class="num tabular">${s.score ?? '—'}<div class="idx-bar"><i style="width:${s.score || 0}%"></i></div></td>
    </tr>`).join('');
  $('rows').querySelectorAll('tr').forEach(tr => tr.onclick = () => focus(tr.dataset.id, true));
}

function renderProvenance(){
  const m = data.manifest;
  $('provenance').innerHTML = Object.entries(m.scenes).map(([role, s]) =>
    `<p><b>${esc({ before: t('prov_role_before'), event: t('prov_role_event'), future: t('prov_role_future') }[role])}:</b> ${esc(s.datetime)}<br><a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.id)}</a></p>`
  ).join('') + `<p><b>${t('prov_osm_label')}</b> ${esc(m.osm.snapshot)}<br><b>${t('prov_download_label')}</b> ${esc(m.downloaded_at)}</p>`;
}

function focus(id, center){
  selected = id;
  const s = data.sites.find(x => x.id === id);
  if (!s) return;
  const forecastText = s.forecast_fraction !== null
    ? tf('forecast_enough', { pct: (s.forecast_fraction * 100).toFixed(1) })
    : t('forecast_insufficient');
  $('focus').innerHTML = `
    <div class="focus-badge">${s.approximate ? t('focus_point_badge') : t('focus_area_badge')}</div>
    <div class="focus-name">${esc(s.name)}</div>
    <div class="focus-signal">${esc(bt(s.signal))}</div>
    <div class="focus-grid">
      <div><div class="f-label">${t('focus_direct_label')}</div><div class="f-val tabular">${pct(s.direct_fraction)}</div></div>
      <div><div class="f-label">${t('th_road')}</div><div class="f-val tabular">${pct(s.road_fraction)}</div></div>
    </div>
    <p class="hint-text">${tf('focus_hint', { forecast: esc(forecastText), u: pct(s.uncertain_fraction) })}</p>
    <p class="hint-text" style="margin-top:8px">${tf('focus_coverage', { c: pct(s.coverage) })}</p>
    <p style="margin-top:10px"><a href="${esc(s.osm_url)}" target="_blank" rel="noreferrer">${t('focus_open_link')}</a></p>`;
  if (center){
    zoom = 2.4;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    pan.x = w / 2 - base.x - s.center[0] * fit * zoom;
    pan.y = h / 2 - base.y - s.center[1] * fit * zoom;
  }
  renderTable();
  draw();
}

function resize(){
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = canvas.clientHeight * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (data){
    fit = Math.min(canvas.clientWidth / data.shape[1], canvas.clientHeight / data.shape[0]);
    base = { x: (canvas.clientWidth - data.shape[1] * fit) / 2, y: (canvas.clientHeight - data.shape[0] * fit) / 2 };
  }
  draw();
}

function pathGeometry(g){
  ctx.beginPath();
  const line = coords => coords.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
  if (g.type === 'Polygon') g.coordinates.forEach(c => { line(c); ctx.closePath() });
  if (g.type === 'MultiPolygon') g.coordinates.forEach(p => p.forEach(c => { line(c); ctx.closePath() }));
  if (g.type === 'LineString') line(g.coordinates);
  if (g.type === 'MultiLineString') g.coordinates.forEach(line);
}

// Map overlay colors intentionally match the backend-rendered PNG layers and
// the on-screen legend 1:1 (cyan = detected water, orange = site exposure,
// purple = forecast, etc.) — these are data encodings, not UI chrome, and
// changing them here without also changing model_v2.py's png() output and
// the legend swatches below would make the legend lie about the map.
function draw(){
  const w = canvas.clientWidth, h = canvas.clientHeight;
  ctx.clearRect(0, 0, w, h);
  if (!data || !images.event) return;
  ctx.save();
  ctx.translate(base.x + pan.x, base.y + pan.y);
  ctx.scale(fit * zoom, fit * zoom);
  const bg = images[['before','event','future'].includes(mode) ? mode : 'event'];
  if (bg) ctx.drawImage(bg, 0, 0);
  if (mode === 'event' && $('watercheck').checked){
    ctx.drawImage(images.flood, 0, 0);
    ctx.drawImage(images.unknown, 0, 0);
  }
  if (['forecast','probability','legacy'].includes(mode)) ctx.drawImage(images[mode], 0, 0);
  if (mode === 'event' && $('uncertaintycheck').checked) ctx.drawImage(images.uncertainty, 0, 0);
  if (mode === 'error' && images.error) ctx.drawImage(images.error, 0, 0);
  if (['event','forecast'].includes(mode) && $('roadcheck').checked){
    ctx.lineWidth = 2 / (fit * zoom);
    ctx.strokeStyle = '#ff7791';
    data.roads.forEach(r => { pathGeometry(r.geometry); ctx.stroke() });
  }
  if ($('sitecheck').checked){
    data.sites.forEach(s => {
      pathGeometry(s.geometry);
      const active = s.id === selected;
      ctx.lineWidth = (active ? 3 : 1.3) / (fit * zoom);
      ctx.strokeStyle = active ? '#ffffff' : s.score === null ? '#a0a7bc' : s.score > 0 ? '#ffb65a' : '#cbfa72';
      ctx.fillStyle = active ? '#ffffff38' : s.score > 0 ? '#ffb65a22' : '#cbfa7210';
      ctx.fill('evenodd');
      ctx.stroke();
    });
  }
  ctx.restore();
}

function setMode(m){
  if ((m === 'future' || m === 'error') && !revealed) return;
  mode = m;
  document.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === m));
  $('stamp').textContent = ({
    before: t('stamp_before'), event: t('stamp_event'), future: t('stamp_future'),
    probability: t('stamp_probability'), legacy: t('stamp_legacy'), forecast: t('stamp_forecast'), error: t('stamp_error'),
  })[m];
  const legendMap = {
    error: [['#31e19e', t('legend_error_hit')], ['#ffb040', t('legend_error_false')], ['#ff4f6e', t('legend_error_missed')]],
    probability: [['#ff0000', t('legend_prob_low')], ['#00c8ff', t('legend_prob_high')]],
    forecast: [['#b480ff', t('legend_forecast_water')], ['#ffb65a', t('legend_site')]],
    legacy: [['#ff9655', t('legend_legacy_water')], ['#ffb65a', t('legend_site')]],
    event: [['#38d7ff', t('legend_event_water')], ['#ffb65a', t('legend_site')], ['#a0a7bc', t('legend_not_evaluable')]],
  };
  $('legend').innerHTML = (legendMap[m] || [['#ffb65a', t('legend_default_site')]])
    .map(([color, label]) => `<span><i class="dot" style="background:${color}"></i>${label}</span>`).join('');
  draw();
}

async function evaluate(){
  const v = await fetchValidation(queryString(params()));
  const s = v.active_forecast, b = v.satellite_persistence;
  const metric = x => x === null ? '—' : (100 * x).toFixed(1) + ' %';
  $('evaluation').innerHTML = `
    <div class="revealnote">${v.deployment === 'learned' ? t('eval_active') : t('eval_persistence_active')} · ${tf('eval_coverage', { v: v.coverage_percent })}</div>
    <div class="eval-grid">
      <div><div class="ev-label">${t('evalgrid_active_f1')}</div><div class="ev-val tabular">${metric(s.f1)}</div></div>
      <div><div class="ev-label">${t('evalgrid_persistence_f1')}</div><div class="ev-val tabular">${metric(b.f1)}</div></div>
      <div><div class="ev-label">${t('evalgrid_precision')}</div><div class="ev-val tabular">${metric(s.precision)}</div></div>
      <div><div class="ev-label">${t('evalgrid_recall')}</div><div class="ev-val tabular">${metric(s.recall)}</div></div>
    </div>
    <p class="hint-text">${esc(bt(v.limitations))}</p>
    <p class="hint-text" style="margin-top:8px">${t('eval_proxy_note')}</p>
    <div class="notice tight">${tf('eval_rejected_notice', {
      f1: (100 * v.rejected_candidate.f1).toFixed(1),
      jf1: (100 * v.additional_temporal_test.learned.f1).toFixed(1),
      jp1: (100 * v.additional_temporal_test.persistence.f1).toFixed(1),
    })}</div>`;
  await loadMarket();
}

async function loadPlan(){
  const p = await fetchTradingPlan(queryString(params()));
  $('tradeplan').textContent = bt(p.action);
}

async function loadMarket(){
  const e = await fetchEventStudy(queryString(params()));
  const r = e.net_return_on_gross_exposure;
  const pts = e.curve.map((p, i) => [20 + i * 460 / Math.max(e.curve.length - 1, 1), p.gross_return_on_gross_exposure]);
  const vals = pts.map(p => p[1]), low = Math.min(0, ...vals), high = Math.max(.001, ...vals);
  const ys = v => 130 - (v - low) / (high - low) * 110;
  const path = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + ys(p[1]).toFixed(1)).join(' ');
  $('marketoutcome').innerHTML = `
    <div class="reveal-lede">${t('market_eyebrow3')}</div>
    <div class="eval-grid" style="margin-top:10px">
      <div><div class="ev-label">${t('market_net_label')}</div><div class="market-return tabular ${r >= 0 ? 'pos' : 'neg'}">${(100 * r).toFixed(2)} %</div></div>
      <div><div class="ev-label">${t('market_agco_label')}</div><div class="market-return tabular">${(100 * e.prices.AGCO.total_return).toFixed(2)} %</div></div>
    </div>
    <svg class="chart-svg" viewBox="0 0 500 155" aria-label="${t('market_svg_al')}"><line x1="20" x2="480" y1="${ys(0)}" y2="${ys(0)}" stroke="#3a4456" stroke-dasharray="4 4"/><path d="${path}" fill="none" stroke="#4c8dff" stroke-width="2.5"/></svg>
    <p class="hint-text" style="margin-top:10px">${tf('market_hint2', { spy: (100 * e.prices.SPY.total_return).toFixed(2), limitations: esc(bt(e.limitations)) })}</p>
    <p class="hint-text" style="margin-top:6px">${tf('market_hint3', { date: esc(e.source.retrieved_at.slice(0, 10)) })}</p>`;
}

$('reveal').onclick = async () => {
  const button = $('reveal');
  button.disabled = true;
  button.textContent = t('reveal_loading');
  try{
    const q = queryString(params());
    [images.future, images.error] = await Promise.all(['future','error'].map(k => loadImage(k, q)));
    await evaluate();
    revealed = true;
    $('futuretab').disabled = false;
    $('futuretab').classList.remove('locked');
    $('errortab').disabled = false;
    $('errortab').classList.remove('locked');
    button.textContent = t('reveal_done');
    setMode('error');
  }catch(e){
    showError(e);
    button.disabled = false;
    button.textContent = t('reveal_retry');
  }
};

$('site-search').oninput = renderTable;
document.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => setMode(b.dataset.mode));
['watercheck','roadcheck','sitecheck','uncertaintycheck'].forEach(id => $(id).onchange = draw);
['threshold','delta','radius'].forEach(id => $(id).oninput = () => {
  $('tv').textContent = (+$('threshold').value).toFixed(2);
  $('dv').textContent = (+$('delta').value).toFixed(2);
  $('rv').textContent = $('radius').value + ' m';
  clearTimeout(timer);
  timer = setTimeout(load, 400);
});

function zoomAt(f, x, y){
  const old = zoom;
  zoom = Math.max(.7, Math.min(12, zoom * f));
  pan.x = x - base.x - (x - base.x - pan.x) * zoom / old;
  pan.y = y - base.y - (y - base.y - pan.y) * zoom / old;
  draw();
}
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const r = canvas.getBoundingClientRect();
  zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX - r.left, e.clientY - r.top);
}, { passive: false });
canvas.onpointerdown = e => { drag = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y, moved: false }; canvas.setPointerCapture(e.pointerId) };
canvas.onpointermove = e => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (Math.abs(dx) + Math.abs(dy) > 5) drag.moved = true;
  pan = { x: drag.px + dx, y: drag.py + dy };
  draw();
};
canvas.onpointerup = e => {
  if (drag && !drag.moved && data){
    const r = canvas.getBoundingClientRect();
    const x = (e.clientX - r.left - base.x - pan.x) / (fit * zoom), y = (e.clientY - r.top - base.y - pan.y) / (fit * zoom);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
    let hit = null;
    for (const s of data.sites){ pathGeometry(s.geometry); if (ctx.isPointInPath(x, y, 'evenodd')){ hit = s; break } }
    ctx.restore();
    if (hit) focus(hit.id, false);
  }
  drag = null;
};
canvas.onpointercancel = () => drag = null;
$('zoomin').onclick = () => zoomAt(1.4, canvas.clientWidth / 2, canvas.clientHeight / 2);
$('zoomout').onclick = () => zoomAt(1 / 1.4, canvas.clientWidth / 2, canvas.clientHeight / 2);
$('reset').onclick = () => { zoom = 1; pan = { x: 0, y: 0 }; draw() };
window.addEventListener('resize', resize);

// ---- language toggle ----
$('langbtn').onclick = () => {
  setLang(getLang() === 'de' ? 'en' : 'de');
  applyI18n();
  if (data){
    renderStats(); renderTable(); renderProvenance(); renderModelInfo();
    setMode(mode);
    if (selected) focus(selected, false);
    loadPlan();
    if (revealed) evaluate();
  }
};

applyI18n();
load();
