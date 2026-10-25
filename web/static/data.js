// Data layer: all communication with the Python backend lives here.
// Nothing in this file touches the DOM. The API contract (endpoint paths,
// response shapes) is owned by app.py / model_v2.py / market.py — this module
// is a thin, typed-in-spirit wrapper around it so the rest of the frontend
// never constructs a fetch URL by hand.

export function queryString({ threshold, delta, radius }){
  return new URLSearchParams({ threshold, delta, radius }).toString();
}

export async function apiGet(path){
  const r = await fetch(path);
  if (!r.ok){
    const body = await r.json();
    throw new Error(body.error || r.statusText);
  }
  return r.json();
}

export function loadImage(kind, q){
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('img_load_fail:' + kind));
    img.src = '/image/' + kind + '.png?' + q;
  });
}

export const fetchAnalysis = q => apiGet('/api/analysis?' + q);
export const fetchValidation = q => apiGet('/api/validation?' + q);
export const fetchTradingPlan = q => apiGet('/api/trading-plan?' + q);
export const fetchEventStudy = q => apiGet('/api/event-study?' + q);

export const exportUrls = q => ({
  csv: '/export/sites.csv?' + q,
  json: '/export/analysis.json?' + q,
});
