# Master prompt: Flood Alpha

Paste this whole file as context when handing this project to another AI (or your future self). It
explains what the project is, why it's built the way it is, exactly how each number on screen is
computed, and the conventions to keep when extending it.

---

## 1. What this is, in one paragraph

Flood Alpha is a local, offline-first Python + vanilla-JS prototype that chains together a full
"satellite intelligence" story for one real historical event — the Canoas, Brazil flood of May
2024 — end to end: archived news/weather alerts flag the area before any image is taken →
real Sentinel-2 imagery confirms the water extent → historical OpenStreetMap industrial sites and
roads become a checkable exposure watchlist with a per-site severity score → a 15-day persistence
forecast is checked against a later, initially-hidden scene → a single-interval statistical
extrapolation estimates how long the flooding will persist, compared against what actually
happened → a fixed hypothetical stock position runs on real AGCO/SPY prices, next to AGCO's real
pre-event segment revenue. Every number in the UI has its computing formula printed next to it
with the real figures plugged in.

**It is a demo/prototype, not a production system or a validated forecasting tool.** Its entire
design philosophy (see §2) is about being transparent about that, loudly and specifically, rather
than papering over the gaps with invented data or vague hedging.

## 2. Non-negotiable project philosophy — read this before changing anything

These rules were established deliberately and are enforced by the existing code/tests/UI copy.
Breaking them silently would be a regression even if the feature "works":

1. **No synthetic or fabricated data, ever.** Every dataset in `data/` is either a real download
   (Sentinel-2, OSM, Yahoo Finance) or a small, hand-curated set of facts with an individual
   citation (`source_url`) per entry — see `data/watch_feed.json`, `data/duration_reference.json`,
   `data/company_financials.json`. If a number can't be sourced, it is not shown. If independent
   sources disagree slightly (e.g. two outlets reporting a slightly different river-gauge reading
   for the same day), both are kept as-is with a note — never silently reconciled or averaged.
2. **State limitations explicitly, next to the result, not buried in a footer.** Nearly every
   metric in the UI is followed by a sentence saying what it is *not* proof of. Keep this pattern
   when adding new metrics.
3. **Future data never leaks into "current" analysis/ranking.** `FloodModel.analyze()` (the 6 May
   signal-day output used for site ranking, severity, and the trading trigger) must never read
   `self.scenes["future"]` (the 21 May scene). Only `FloodModel.evaluate()` (called after the user
   clicks "Fast-forward") touches it. This is enforced by a test:
   `tests/test_core.py: test_event_result_does_not_use_future_scene`. If you touch `analyze()`,
   keep this test green.
4. **Every formula is shown next to its result, with real numbers plugged in**, in a small
   monospace `.formula` div (see §8). This was added deliberately so the app is self-documenting —
   a user (or another AI) can verify any number by reading the line directly below it. Any new
   computed metric should follow this pattern.
5. **English only**, UI and code comments. The project was originally a German-language prototype
   and was fully translated; don't reintroduce non-English strings.
6. **Offline-reproducible after first install.** No API keys, no live network calls at runtime
   (`fetch_data.py` and `market.py --fetch` are the only things that touch the network, and only
   when explicitly re-run). The bundled `data/` must be sufficient to run everything.
7. **Single historical case study, not a general tool.** The AOI, dates, company mapping (AGCO ↔
   `way/475623590`), and all curated facts are specific to the Canoas/May-2024 event. Don't
   generalize to "any event" without the user asking for that — it's a deliberate scope decision
   from an earlier turn in this project's history.

## 3. How this project got here (so you understand *why*, not just *what*)

1. An AI-generated first prototype existed (German UI, README, code) implementing: before/after
   Sentinel-2 imagery, water-change detection, industrial-site/road exposure, a 15-day persistence
   forecast validated against a later scene, and a hypothetical AGCO/SPY trading case study.
2. The user supplied a brainstorm list of desired MVP features and asked for a full rebuild in
   English, structured around that list. Two features were net-new and didn't exist in the
   original prototype:
   - "use news and weather forecasts to predict where to look"
   - "use news, satellite images etc. to predict how long the flooding will persist"
3. These were implemented as **archived historical replays**, not live integrations (an explicit
   scope choice — see §2 rule 1 and 6): a cited alert timeline (`watch.py` /
   `data/watch_feed.json`) for the first, and a single-interval exponential recession
   extrapolation (`model.py: recession_estimate`) compared against a real-world precedent
   (`data/duration_reference.json`) for the second.
4. The user then asked for: a chart of the alert escalation, a "weather forecast" panel, and a
   clear visualization of the drying prediction — implemented as an SVG step chart of alert levels,
   real river-gauge stat cards, and an SVG exponential-decay curve chart with solid (observed) vs.
   dashed (extrapolated) segments and a real-world comparison line.
5. The user then asked for a formula next to every forecast/computed value — implemented as the
   `.formula` monospace annotations described in §8, added to all ~10 distinct computed metrics in
   the UI, each with real numbers plugged in (verified in-browser to match the displayed result).

Read these five steps as the actual order of intent — it explains design choices like "why is the
duration chart split solid/dashed" (because only day 0 and day 15 are *observed*; everything else
is *extrapolated*, and the UI makes that distinction load-bearing, not cosmetic).

## 4. Repository map

```
app.py              Local HTTP server (stdlib only). Routes, parameter validation, CSV/JSON export.
model.py            Raster processing: water detection, site exposure/severity, forecast,
                     evaluation against the later scene, duration-recession heuristic, PNG overlays.
watch.py            Loads/summarizes the archived news-weather alert timeline.
market.py           Real price download, real pre-event company financials, fixed trading rule,
                     hypothetical P&L accounting.
fetch_data.py        Downloads Sentinel-2 crops + historical OSM data (network, run manually).
web/index.html       Entire frontend: HTML + CSS + vanilla JS in one file, no build step, no
                     external JS libraries (self-imposed constraint — see footer: "no external
                     map libraries").
data/                Real downloaded imagery/OSM/market data + manually curated, cited JSON facts.
tests/test_core.py   Unit + integration tests against the bundled real data.
analysis.json, validation.json, event_study.json, watch_feed_summary.json
                     Pre-computed outputs with default parameters (regenerate with `python app.py
                     --export`).
README.md            User-facing documentation (English), feature-to-brainstorm mapping table.
TEST_RESULTS.txt     Captured output of the last full test run.
run.sh               `bash run.sh` — creates .venv, installs requirements.txt, runs app.py.
```

## 5. Data assets and what's real about each

| File | What it is | Real / curated |
|---|---|---|
| `data/before.npz`, `event.npz`, `future.npz` | Sentinel-2 L2A band crops (B02/B03/B04/B11/SCL), 21 Apr / 6 May / 21 May 2024, EPSG:32722, 20 m, 945×1114 px | Real download, Copernicus via Planetary Computer |
| `data/manifest.json` | Grid transform, scene IDs/dates, SHA-256 checksums | Generated by `fetch_data.py` |
| `data/osm.json` | Industrial landuse, `man_made=works`, and major roads, snapshot dated **24 Apr 2024** (before the event) | Real, via Overpass API historical query |
| `data/market_AGCO.json`, `market_SPY.json`, `market_manifest.json` | Daily OHLC + dividends, Apr–Jun 2024 | Real, Yahoo Finance chart API |
| `data/watch_feed.json` | 8 dated entries (22 Apr–6 May 2024): weather alerts, river-gauge readings, news, each with its own `source`/`source_url`; `level` ∈ {advisory, watch, warning, emergency, satellite}; river entries carry a numeric `level_m`; `historical_record` = the 1941 flood level (4.76 m) | Manually curated, individually cited (Wikipedia, Al Jazeera, a PAM 2025 arXiv preprint, Washington Post/AP) — **not** a live feed |
| `data/duration_reference.json` | Real-world Guaíba-gauge recession timeline, 29 Apr–7 Jun 2024; `days_after_signal_fully_receded: 32` | Manually curated, cited to the same PAM 2025 preprint |
| `data/company_financials.json` | AGCO FY2023 net sales by region (South America $2,234.2M / $14,412.4M total, 15.5%), filed 6 Feb 2024 — **before** the event | Real, AGCO's own Q4/FY2023 earnings release |

None of these three curated JSON files are touched by `fetch_data.py` — they are committed facts,
not downloads. If you add a new curated fact, give it a `source` and `source_url` field and cite it
in the UI, matching this pattern exactly.

## 6. The six MVP features → implementation (what the user actually asked for)

| Brainstormed feature | Where it lives |
|---|---|
| Before/after satellite image | `model.py: FloodModel.png()`, `/image/{before,event,future}.png` |
| Identify affected areas | `model.py: FloodModel.masks()` — MNDWI water-change detection |
| Identify affected roads | `model.py: FloodModel.analyze()` — road-buffer wet-fraction |
| Identify affected companies + severity + compare with financial figures | `model.py: analyze()` (per-site `severity`/`severity_level`/`score`) + `market.py: financial_profile()` (AGCO's real segment revenue) |
| Use news/weather to predict where to look | `watch.py`, `data/watch_feed.json`, `/api/watch-feed`, the Step 1 panel (timeline + escalation chart + river cards) |
| Predict how long flooding will persist | `model.py: recession_estimate()`, `site_duration()`, `/api/validation`'s `duration`/`site_duration` keys, the Step 4 panel (curve chart + two stat boxes) |

## 7. The computational pipeline, with exact formulas

### 7.1 Water detection (`model.py: FloodModel.masks`)

```
MNDWI = (B03 − B11) / (B03 + B11)          # on scaled/offset reflectances, common 20m grid
valid  = ~dilate(SCL ∈ {0,1,2,3,8,9,10,11}, 2px) & B03>0 & B11>0 & denom>0.001
permanent = (MNDWI_before > threshold) & valid_before
new_water = valid & ~permanent & (MNDWI_event > threshold) & (MNDWI_event − MNDWI_before > delta)
new_water = remove connected components < 25 px (1 ha)
```
Defaults: `threshold=0.15`, `delta=0.18`, user-adjustable via sliders (query params
`threshold`/`delta`, validated in `app.py: parameters()`, range-checked, `lru_cache`d per
parameter combo in `model.py`).

### 7.2 Site exposure & severity (`model.py: analyze`)

```
direct_fraction = flooded px in site footprint / valid px in site footprint
road_fraction   = wet road px within {radius}m / valid road px within {radius}m   (radius default 500m)
coverage        = valid footprint px / total footprint px   — sites below 80% coverage are NOT scored
severity_score  = 70 × direct_fraction + 30 × road_fraction        (0 when not scored)
severity_level  = 0 data-gap | 1 none | 2 indirect (road≥0.10) | 3 direct (direct≥0.05)
```
Roads tagged `bridge`/`tunnel` are excluded from the wet-road mask. This is a **ranking
heuristic, not a calibrated probability** — say so if you touch the copy.

### 7.3 Forward forecast + evaluation (`model.py: analyze` / `evaluate`)

- Forecast ("persistence"): flood mask frozen at 6 May is the prediction for 21 May. Computed in
  `analyze()`, which **never reads the future scene** (rule #3 in §2).
- Evaluation (`evaluate()`, only called after "Fast-forward"):
```
comparison = valid_event & valid_future & ~permanent
observed   = clean_components(MNDWI_future > threshold)
binary_scores(prediction=new_water, target=observed, valid=comparison):
  precision = TP/(TP+FP)   recall = TP/(TP+FN)   F1 = 2·TP/(2·TP+FP+FN)   IoU = TP/(TP+FP+FN)
baseline = binary_scores(all-false, observed, comparison)      # "no new flooding" weak reference
```

### 7.4 Duration / recession extrapolation (`model.py: recession_estimate`, `site_duration`)

Single-interval exponential-decay fit — **deliberately simple, deliberately labeled as
illustrative, not predictive**:
```
persisted_fraction = (flooded-&-still-wet px at day 15) / (flooded px at day 0)
k      = −ln(persisted_fraction) / 15                      # fitted daily decay rate
t_dry  = ln(dry_threshold) / −k                             # dry_threshold default 0.10
status: "extrapolated" | "drained_by_day15" (persisted≤0) | "no_measurable_recession" (persisted≥1)
        | "no_new_water" (day0=0)
```
Run both area-wide (`evaluate()`'s `duration` key) and per eligible site (`site_duration()`,
keyed by site id — only sites with `event_n>0`). Compared in the UI against
`duration_reference.json`'s real `days_after_signal_fully_receded` — **the two are expected to
differ**; that mismatch is the point, not a bug to "fix" by tuning the heuristic.

### 7.5 News/weather escalation (`watch.py: feed`)

Not a model — chronological sort + a date subtraction:
```
level_rank ∈ {advisory:1, watch:2, warning:3, emergency:4}
lead_time_days      = satellite_signal_date − first_alert_date
peak_lead_time_days = satellite_signal_date − date_of_max(level_rank)
```
`feed()` also derives `level_series` (for the escalation chart) and `river_level_series` /
`historical_record` (for the river cards) straight from the same entries — never duplicate these
numbers elsewhere; always derive from `data/watch_feed.json`.

### 7.6 Financial profile & hypothetical trade (`market.py`)

```
south_america_share_percent = south_america_net_sales / total_net_sales × 100
trigger  = direct_fraction ≥ 0.05  ∨  road_fraction ≥ 0.10          (evaluated on the AGCO site)
total_return(ticker, day) = (close − entry_open + Σ dividends since entry) / entry_open
gross    = −AGCO_total_return + SPY_total_return          (short AGCO notional $1, long SPY $1)
costs    = 0.001×4 (10bp × 4 executions) + 0.05×days_held/365 (flat annual borrow)
net      = gross − costs
net_return_on_gross_exposure = net / 2                     # $2 initial gross exposure
```
Entry 2024-05-07 open, exit 2024-05-21 close, hardcoded (`market.py: plan()`). No real order is
ever sent; this is explicitly a hypothetical, retrospectively-designed case study.

## 8. Frontend conventions (`web/index.html` — single file, no build step)

- **Five numbered steps**, top to bottom, matching the narrative in §6: Step 1 (news/weather) →
  Step 2 (satellite map, before/signal/outcome/error/recession tabs) → Step 3 (watchlist table) →
  Step 4 (duration) → Step 5 (company/trade). Keep this ordering and numbering if you add a step.
- **Formula convention**: any computed number gets a `<div class="formula">...</div>` directly
  below it, monospace, muted color (`#7d93b2`), showing the symbolic formula *and* — wherever the
  data is available client-side — the real numbers plugged in (e.g.
  `score = 70×68.9 + 30×12.6 = 52`). This is a hard pattern now; don't add a new metric without it.
- **Reveal gating**: `revealed` (JS global) gates access to the 21 May scene, the "Forecast error"
  and "Recession" map tabs, the evaluation panel, the duration chart, and the market outcome — all
  unlocked together by the single "Fast-forward 15 days" button (`$('reveal').onclick`). Don't let
  any future-scene-derived UI render before this.
- **Charts are hand-rolled inline SVG**, not a charting library (no external JS beyond the page
  itself — see the footer's explicit "no external map libraries" claim). Pattern: build path
  strings with template literals, `X()`/`Y()` scale closures, `padL/padR/padT/padB` margins. See
  `renderEscalationChart`, `renderDurationCurve`, and the market-outcome sparkline in `loadMarket`
  for the established style.
- **Color system** (CSS vars in `:root`): `--cyan #51dcff` (primary/observed), `--lime #cbfa72`
  (positive/real-world), `--orange #ffb65a` (warning/model estimate), `--red #ff6a87`
  (negative/emergency), `--muted #9aaec6`. Alert-level colors:
  `{advisory:#9fd2ff, watch:#cbfa72, warning:#ffb65a, emergency:#ff6a87}`.
- **The map** (`<canvas id="map">`) is a hand-rolled pan/zoom raster+vector renderer — PNG base
  layers from `/image/*`, GeoJSON overlays in pixel space from `/api/analysis`'s `geometry` fields,
  rendered with `pathGeometry()` + `ctx.isPointInPath` for click-hit-testing. Not a mapping
  library.

## 9. API surface (`app.py`)

All routes accept `?threshold=&delta=&radius=` (validated by `parameters()`; ignored where
irrelevant, e.g. `/health`).

| Route | Returns |
|---|---|
| `GET /` | `web/index.html` |
| `GET /health` | status + site count |
| `GET /api/analysis` | `FloodModel.analyze()` — sites, roads, summary, parameters, manifest |
| `GET /api/validation` | `FloodModel.evaluate()` — scores, duration, site_duration (future-scene dependent) |
| `GET /api/watch-feed` | `watch.feed()` |
| `GET /api/trading-plan` | `market.plan(analyze())` — includes `financial_profile` |
| `GET /api/event-study` | `market.event_study(analyze())` — full P&L breakdown |
| `GET /image/{before,event,future,flood,unknown,error,recession}.png` | Rendered PNG layer |
| `GET /export/sites.csv` | CSV of `analyze()["sites"]`, formula-injection-safe |
| `GET /export/analysis.json` | Full `analyze()` as a download |
| `GET /export/{watch-feed,duration-reference,company-financials}.json` | Raw passthrough of the matching `data/*.json` file (see `RAW_EXPORTS` dict in `app.py`) |

`python app.py --export` writes `analysis.json`, `validation.json`, `event_study.json`,
`watch_feed_summary.json` at the repo root with default parameters (no server).

## 10. Dev workflow

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt   # or: bash run.sh
.venv/bin/python app.py                       # serves http://127.0.0.1:8765
.venv/bin/python -m unittest discover -s tests -v   # 15 tests, should stay green
.venv/bin/python app.py --export              # regenerate root-level pre-computed JSON
.venv/bin/python fetch_data.py --force        # full re-download (needs internet)
```
Syntax-check the embedded JS without a browser:
```bash
python3 -c "c=open('web/index.html').read(); open('/tmp/x.js','w').write(c[c.index('<script>')+8:c.index('</script>')])"
node --check /tmp/x.js
```

## 11. Test suite map (`tests/test_core.py`, 15 tests)

- `NumericalTests`: `binary_scores` confusion-matrix math, `clean_components` component filtering,
  `recession_estimate` bounds/monotonicity, parameter validation rejects NaN/inf/zero-radius.
- `WatchFeedTests`: feed entries sorted, every entry cites a real URL, peak level is "emergency"
  and precedes the satellite date.
- `RealDataTests` (loads the real `FloodModel` once, `setUpClass`): data-integrity checksums,
  OSM-snapshot-predates-event-scene, **future-scene isolation** (critical — see §2 rule 3),
  real spatial analysis sanity bounds, duration-extrapolation presence/consistency, no-position
  edge case, real market cost accounting, financial-profile sum-check, all PNG kinds decode.

## 12. Known gaps — stated on purpose, don't silently "fix" by inventing data

- News/weather is a fixed historical replay of one event, not a live feed or a generalizable
  where-to-look model (no NLP, no geocoding, no multi-region scoring).
- Duration extrapolation is fit from a single two-point interval of a single event; it has no
  external driver (rainfall, dam releases, drainage infra) and is explicitly expected to diverge
  from the real-world precedent (it does: 83.4d model vs. 32d real, area-wide).
- Severity score / exposure index is an unvalidated heuristic, not a calibrated failure
  probability or trading signal.
- The trading case study is a single retrospective rule on one company; no causality, no
  news/weather comparison, no slippage/funding/variable-borrow modeling beyond the flat
  assumptions in §7.6.
- Validation's "ground truth" (21 May scene) uses the same sensor/index as the prediction — not an
  independent measurement.
- Single AOI, single event, single company (AGCO) — not generalized, by deliberate scope choice.

## 13. If you're an AI picking this up cold — orientation checklist

1. Read §2 (philosophy) and §3 (history) first — most "why is it built like that" questions are
   answered there.
2. `cd flood_alpha && .venv/bin/python app.py` (create the venv first if absent — see §10), open
   `http://127.0.0.1:8765`, click through Steps 1–5, then click "Fast-forward 15 days".
3. Run the test suite before and after any change — it's fast (~2s) and encodes the invariants
   that matter most (future-scene isolation, data integrity, cost accounting).
4. Before adding any new fact/number: does it have a real, citable source? If not, don't add it.
   If yes, follow the pattern in `data/watch_feed.json` / `company_financials.json` (a `source` +
   `source_url` per fact) and show its formula next to it in the UI per §8.
5. Before editing `model.py: analyze()`: confirm you're not introducing a read of
   `self.scenes["future"]` — that's the one line you must never cross.
