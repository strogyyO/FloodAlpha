// Alt-data demo terminal — a self-contained, illustrative sandbox unrelated
// to the flood/market analysis in app.js. Deliberately has no shared state
// with it (see DESIGN_INTEGRATION.md): it only shares the i18n layer.
//
// Everything this module displays is clearly labeled: the "sensor" data is
// synthetic (real price + random noise, shown as such in quant_demo.py's
// response), and the "signal" is a random demo outcome, not analysis.
import { t, tf } from './i18n.js';

const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const SUPPORTED = ['TSLA', 'WMT', 'NKE', 'XOM', 'CAT'];

let currentTicker = '';
let lastProxies = null, lastDetail = null, lastSignal = null;

async function getJSON(path){
  const r = await fetch(path);
  return r.json();
}

async function scan(){
  const ticker = ($('quant-ticker').value || '').trim().toUpperCase();
  if (!ticker) return;
  currentTicker = ticker;
  $('quant-status').textContent = t('quant_loading');
  $('quant-proxylist').innerHTML = '';
  $('quant-detail').innerHTML = `<p class="quant-chart-empty">${t('quant_chart_empty')}</p>`;
  $('quant-chart-title').textContent = t('quant_chart_empty_title');
  $('quant-chart-edge').textContent = '';
  $('quant-signal').innerHTML = `<p class="hint-text">${t('quant_signal_empty')}</p>`;

  const res = await getJSON('/api/quant/proxies?ticker=' + encodeURIComponent(ticker));
  if (!res.success){
    $('quant-status').textContent = '';
    $('quant-proxylist').innerHTML = `<p class="hint-text">${esc(tf('quant_unsupported', { ticker: esc(ticker), list: SUPPORTED.join(', ') }))}</p>`;
    return;
  }
  $('quant-status').textContent = '';
  lastProxies = res.data.proxies;
  lastDetail = null;
  lastSignal = null;
  renderProxyList(lastProxies);
  renderSignalButton();
}

function renderProxyList(proxies){
  $('quant-proxylist').innerHTML = '';
  proxies.forEach(proxy => {
    const card = document.createElement('div');
    card.className = 'proxy-card' + (lastDetail && lastDetail.proxy.id === proxy.id ? ' active' : '');
    card.innerHTML = `<div class="p-name">${esc(proxy.name)}</div><div class="p-meta">${esc(proxy.metric)} · <span class="edge">${esc(proxy.edge)}</span></div>`;
    card.onclick = () => {
      $('quant-proxylist').querySelectorAll('.proxy-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      loadDeepDive(proxy);
    };
    $('quant-proxylist').appendChild(card);
  });
}

async function loadDeepDive(proxy){
  $('quant-chart-title').textContent = proxy.name;
  $('quant-chart-edge').textContent = tf('quant_edge_label', { edge: proxy.edge });
  $('quant-detail').innerHTML = `<p class="quant-chart-empty">${t('quant_loading')}</p>`;

  const res = await getJSON('/api/quant/sensor?ticker=' + encodeURIComponent(currentTicker) + '&proxy_id=' + encodeURIComponent(proxy.id));
  if (!res.success){
    $('quant-detail').innerHTML = `<p class="quant-chart-empty">${esc(res.error || '')}</p>`;
    return;
  }
  const d = res.data;
  lastDetail = { proxy, data: d };
  renderDetail(proxy, d);
}

function renderDetail(proxy, d){
  $('quant-chart-title').textContent = proxy.name;
  $('quant-chart-edge').textContent = tf('quant_edge_label', { edge: proxy.edge });
  const note = d.real_stock_baseline ? t('quant_sim_note_full') : t('quant_sim_note_fallback');
  $('quant-detail').innerHTML = `
    <div class="quant-info-grid">
      <div class="quant-info-box"><h5>${t('quant_mechanism')}</h5><p>${esc(proxy.mechanism)}</p></div>
      <div class="quant-info-box"><h5>${t('quant_financial')}</h5><p>${esc(proxy.financial_transmission)}</p></div>
      <div class="quant-info-box"><h5>${t('quant_edge')}</h5><p>${esc(proxy.deep_dive)}</p></div>
    </div>
    <span class="quant-sim-tag">${t('quant_sim_tag')}</span>
    ${renderChart(d)}
    <p class="hint-text" style="margin-top:8px">${esc(note)}</p>`;
}

function renderChart(d){
  const w = 600, h = 160, pad = 8;
  const scale = (vals) => {
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const span = (hi - lo) || 1;
    return v => h - pad - ((v - lo) / span) * (h - 2 * pad);
  };
  const xAt = i => pad + i * (w - 2 * pad) / Math.max(d.values.length - 1, 1);
  const yProxy = scale(d.values);
  const proxyPath = d.values.map((v, i) => (i ? 'L' : 'M') + xAt(i).toFixed(1) + ',' + yProxy(v).toFixed(1)).join(' ');

  let realPath = '';
  if (d.real_stock_baseline && d.real_stock_baseline.values.length){
    const yReal = scale(d.real_stock_baseline.values);
    realPath = d.real_stock_baseline.values.map((v, i) => (i ? 'L' : 'M') + xAt(i).toFixed(1) + ',' + yReal(v).toFixed(1)).join(' ');
  }

  return `
    <svg class="chart-svg" style="margin-top:14px" viewBox="0 0 ${w} ${h}" role="img">
      ${realPath ? `<path d="${realPath}" fill="none" stroke="#8d9aa0" stroke-width="1.5" stroke-dasharray="4 3"/>` : ''}
      <path d="${proxyPath}" fill="none" stroke="#247a83" stroke-width="2.2"/>
    </svg>
    <div class="quant-chart-legend">
      <span><i class="swatch" style="background:#247a83"></i>${t('quant_legend_proxy')}</span>
      ${d.real_stock_baseline ? `<span><i class="swatch" style="background:#8d9aa0"></i>${t('quant_legend_real')}</span>` : ''}
    </div>`;
}

function renderSignalButton(){
  $('quant-signal').innerHTML = `<button class="btn-primary" id="quant-signal-btn" style="width:100%">${t('quant_signal_btn')}</button>`;
  $('quant-signal-btn').onclick = generateSignal;
}

async function generateSignal(){
  const btn = $('quant-signal-btn');
  btn.disabled = true;
  const res = await getJSON('/api/quant/signal?ticker=' + encodeURIComponent(currentTicker));
  btn.disabled = false;
  if (!res.success) return;
  lastSignal = res.data;
  renderSignal(lastSignal);
}

function renderSignal(d){
  const long = d.action.startsWith('LONG');
  $('quant-signal').innerHTML = `
    <span class="quant-sim-tag">${t('quant_sim_tag')}</span>
    <div class="signal-action ${long ? 'long' : 'short'}">${esc(d.action)}</div>
    <p class="hint-text">${esc(d.rationale)}</p>
    <div class="eval-grid" style="margin-top:10px">
      <div><div class="ev-label">${t('quant_confidence')}</div><div class="ev-val tabular">${d.confidence}%</div></div>
      <div><div class="ev-label">${t('quant_hedge')}</div><div class="ev-val tabular" style="font-size:14px">${esc(d.hedge)}</div></div>
    </div>
    <p class="hint-text" style="margin-top:8px">${t('quant_stoploss')}: ${esc(d.stop_loss)}</p>
    <button class="btn-primary" id="quant-signal-btn" style="width:100%;margin-top:10px">${t('quant_signal_btn')}</button>`;
  $('quant-signal-btn').onclick = generateSignal;
}

$('quant-scan').onclick = scan;
$('quant-ticker').addEventListener('keydown', e => { if (e.key === 'Enter') scan(); });

// Re-render any already-displayed quant content in the new language when the
// main app's language toggle fires. Uses addEventListener (not .onclick=) so
// this doesn't clobber app.js's own handler on the same button, and re-renders
// from cached data rather than re-fetching (no extra network calls on toggle).
$('langbtn').addEventListener('click', () => {
  if (lastProxies) renderProxyList(lastProxies);
  if (lastDetail) renderDetail(lastDetail.proxy, lastDetail.data);
  if (lastSignal) renderSignal(lastSignal);
  else if (lastProxies) renderSignalButton();
});
