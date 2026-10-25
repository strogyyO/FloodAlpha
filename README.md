# Flood Alpha — runnable Python prototype on real data

Historical case study of the Canoas, Brazil flood, May 2024.

The app chains together the MVP idea end to end: archived news/weather alerts flag the area
before any image is taken; real satellite imagery then confirms the water extent; historical
industrial sites and roads turn that into a checkable exposure watchlist with a severity call
and real financial context per company; a 15-day persistence forecast and a duration estimate
are checked against a later, initially hidden scene; and a fixed hypothetical stock position
runs on real AGCO/SPY prices.

## MVP feature map

This rebuild maps directly onto the original brainstorm:

| Brainstormed feature | Where it lives |
|---|---|
| Before and after satellite image | Step 2 — Sentinel-2 before/signal/outcome passes (`model.py`, `/image/*`) |
| Identifying affected areas | Step 2 — MNDWI water-change detection (`model.py: masks`) |
| Identifying affected roads | Step 3 — wet-road-catchment analysis (`model.py: analyze`, road rows) |
| Identifying affected companies + severity classification, compared with financial figures | Step 3 (per-site severity) + Step 5 (AGCO real segment revenue) (`model.py`, `market.py`) |
| Use news and weather forecasts to predict where to look | Step 1 — archived, cited alert timeline (`watch.py`, `data/watch_feed.json`) |
| Predict how long the flooding will persist | Step 4 — single-interval recession extrapolation vs. the real-world precedent (`model.py: recession_estimate`, `data/duration_reference.json`) |

## Start

Python 3.10 or newer, 3.12–3.14 recommended. Unzip and, inside the `flood_alpha` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open in a browser: **http://127.0.0.1:8765**

Windows: use `.venv\Scripts\activate` instead of `source`; `python` instead of `python3` if needed.

On macOS/Linux you can also run `bash run.sh`. The first install needs internet. After that, the
bundled case study runs fully offline: no API keys, no external map tiles, no cloud app. The
bundled imagery and OSM data are real downloaded extracts, not simulated. The small weather/news
and financial datasets (see below) are manually curated from public reporting, each entry citing
its own source — not a live feed.

## Three-minute demo

1. **Step 1 — News & weather.** Read the archived alert timeline: a storm advisory is already on
   record 14 days before the satellite ever captures the flood.
2. **Step 2 — Satellite.** Switch from **21 Apr · before** to **06 May · signal**: explore new
   water extent and site exposure.
3. **Step 3 — Watchlist.** Click a site in the table. Direct exposure and nearby wet roads are
   reported separately, each with a severity label. AGCO South America is in the list.
4. **Step 4 — Duration (before reveal).** See the real-world precedent for how long this event's
   floodwaters actually took to recede, before any model-based estimate is shown.
5. **Step 5 — Company.** Look at AGCO's real, pre-event segment revenue and the fixed hypothetical
   trading rule; its price outcome stays hidden for now.
6. **Fast-forward 15 days**: the 21 May scene, the forecast-error map, the recession layer, the
   duration model's own extrapolation, and the actual price history all unlock together.
7. Export CSV or JSON. Change parameters and explore sensitivity. After revealing, changes are
   exploratory, not a fresh untouched test.

## Data and dates

| Component | Source | Period |
|---|---|---|
| Before scene | Copernicus Sentinel-2 L2A, tile 22JDN | 21 Apr 2024 |
| Signal scene | Copernicus Sentinel-2 L2A, tile 22JDN | 06 May 2024 |
| Later observation | Copernicus Sentinel-2 L2A, tile 22JDN | 21 May 2024 |
| Industrial sites, roads, bridges | Historical OpenStreetMap snapshot via Overpass | 24 Apr 2024 |
| AGCO and SPY | Yahoo Finance, daily open/close prices and dividends | Apr–Jun 2024 |
| AGCO ↔ Canoas mapping | AGCO 2023 Form 10-K, SEC | published before the event |
| AGCO FY2023 segment net sales | AGCO press release, 6 Feb 2024 | published before the event |
| News/weather alert timeline | Wikipedia, Al Jazeera, a PAM 2025 preprint, Washington Post/AP (each entry cited individually) | 22 Apr – 06 May 2024 |
| Flood-duration real-world precedent | Same PAM 2025 preprint (Guaíba gauge, Porto Alegre) | 29 Apr – 07 Jun 2024 |

Analysis area: 51.30°W to 51.07°W, 29.91°S to 29.74°S. Shared grid: EPSG:32722, 20 m, 1114 × 945
pixels. Reflectance bands B02/B03/B04/B11 and the SCL scene classification live compressed in
`data/`. The individual scenes, original STAC metadata, original OSM objects, market price
responses and SHA-256 checksums are included. No temporarily signed download URLs are stored.

Primary sources and access:

- [Planetary Computer / Sentinel-2](https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a)
- [Copernicus Sentinel-2](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2)
- [Historical Overpass queries](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#date)
- [AGCO 2023 10-K, SEC](https://www.sec.gov/Archives/edgar/data/880266/000088026624000013/agco-20231231.htm)
- [AGCO Q4/FY2023 results, 6 Feb 2024](https://news.agcocorp.com/2024-02-06-AGCO-REPORTS-FOURTH-QUARTER-AND-FULL-YEAR-RESULTS)
- [2024 Rio Grande do Sul floods (Wikipedia)](https://en.wikipedia.org/wiki/2024_Rio_Grande_do_Sul_floods)
- [Al Jazeera, 5 May 2024](https://www.aljazeera.com/news/2024/5/5/at-least-75-killed-more-than-100-others-missing-in-brazil-floods)
- ["30 Days of Flooding" (PAM 2025 preprint, arXiv:2509.04219)](https://arxiv.org/html/2509.04219v1)
- Exact scene and data URLs are in `data/manifest.json` and `data/market_manifest.json`. Each
  news/weather and financial entry cites its own `source_url` in `data/watch_feed.json`,
  `data/duration_reference.json` and `data/company_financials.json`.

Archive retrieval happened when this prototype was built. Scene dates and today's STAC metadata
do not prove when a market participant could actually have obtained the image at the time.
Historical publication and processing latency are not reconstructed.

## What is computed

### Step 1 — News and weather, before any image (`watch.py`)

A fixed, dated, cited record of public weather alerts and news reports for the Rio Grande do
Sul / Porto Alegre area, from a Civil Defense advisory on 22 April through the satellite signal
scene on 6 May. No live news or weather API is called — this is archived history, in the same
offline spirit as the rest of the app. Each entry carries its own source and URL. The feed
reports how many days before the satellite signal the alerts first escalated, and when they
peaked, to make the point concrete: **in a live deployment, a feed like this — not the
satellite — is what would trigger tasking a fresh image of an area in the first place.**
Independently reported numbers that differ slightly across outlets (e.g. the exact river-gauge
reading on a given day) are shown as-is, not reconciled into one figure.

### Water detection (Step 2)

MNDWI = (B03 − B11) / (B03 + B11), on reflectances with correct scaling and additive offset. The
bands are brought to a shared 20 m grid. SCL classes 0, 1, 2, 3, 8, 9, 10 and 11 are excluded to
mask invalid pixels, dark areas, shadow, cloud and snow. The mask edge is grown by two pixels.

New water pixels on 6 May must satisfy, simultaneously:

- valid on both 21 April and 6 May;
- MNDWI ≤ water threshold before;
- MNDWI > water threshold on 6 May;
- MNDWI increase > change threshold.

Connected patches under 25 pixels (1 ha) are removed. Defaults: water threshold 0.15, change
threshold 0.18. This is a traceable spectral heuristic, not a trained segmentation model. No
invented flood-detection accuracy figure is reported.

### Exposure and severity (Step 3)

OSM industrial areas are intersected with new water. OSM point features have no documented
factory footprint and are explicitly flagged as a 60 m approximation. Generic industrial-landuse
polygons that contain named production sites are removed to avoid some double counting; full
entity resolution is not guaranteed.

Roads are rasterized with a 10 m buffer. The share of wet road pixels in the adjustable site
catchment is a check flag. Bridges and tunnels are excluded. There is **no** traffic-flow
analysis and **no** evidence of missing alternative routes.

Each site gets a **severity label** — data gap, no image signal, indirect exposure (wet access
roads), or direct exposure — plus a heuristic **severity score** = 70 × directly-exposed area
fraction + 30 × wet-road fraction. Sites below 80% valid area coverage are not scored. This
index is not a calibrated failure probability.

### Real forward forecast with a simple model (Step 2/3)

The persistence approach, frozen on 6 May, predicts: newly detected water stays wet on 21 May.
The future dataset is not used in the forecast or the site ranking; that is tested (see
`tests/test_core.py: test_event_result_does_not_use_future_scene`). Only the evaluation step
touches it, after you choose to reveal it.

F1, precision, recall and IoU are computed only on pixels valid in all three scenes that were
previously dry. The comparison method is "no new water." That is deliberately a weak baseline. A
meaningful weather/gauge comparison is still missing.

The 21 May reference comes from the **same sensor and the same water index**. It is a later
observation, not independent ground truth. The metrics score water persistence, not operational
outages. This is a single spatially connected event; pixels are not independent test cases.

### Flood-duration estimate (Step 4, `model.py: recession_estimate`)

After you reveal the 21 May scene, the app fits one exponential decay rate from how much of the
6-May flooded area was still wet on 21 May, and extrapolates the day on which roughly 10% of the
original flooded area would remain wet — both area-wide and per site. This is a transparent,
single-interval heuristic, explicitly **not** a calibrated hydrological model: it assumes a
constant daily recession rate, which real drainage (pumping, dams, further rain, local
infrastructure) will not actually hold. It is shown next to a real-world precedent — how long the
Guaíba river gauge at Porto Alegre (a metro-area measurement, not a per-site one) actually took to
recede after this event — so the two can be compared, not conflated. They are expected to differ:
the AGCO site itself, for instance, was already dry by 21 May even though the area-wide
extrapolation runs much longer, which is a real property of this one event, not a bug.

### Hypothetical trading rule with real prices, and real financial scale (Step 5)

The AGCO OSM area `way/475623590` is mapped by name and by the Canoas location documented in the
SEC company source. This mapping is manually curated, not an automatic global company resolution.

Alongside the trade, the app shows AGCO's real **FY2023 South America segment net sales**
($2,234.2M of $14,412.4M total, 15.5%), filed on 6 February 2024 — before the flood, so it is not
itself a reaction to the event. This is the scale of the region containing the exposed site, not
a Canoas-facility-specific figure: AGCO does not publicly disclose single-facility revenue.

Fixed demonstration rule: ≥5% direct area exposure or ≥10% wet road catchment → short AGCO and
long SPY, $1 initial notional each; otherwise no position. No order is ever sent. Entry on 7 May
2024 at the open, exit on 21 May at the close. The period, instruments and thresholds are a
retrospectively designed case study, not a pre-registered trading test.

- Share counts are computed at entry from price and not rebalanced daily.
- Cash dividends between entry and exit are credited or charged as a short obligation; no
  reinvestment.
- Transaction costs: 10 basis points per execution on the initial notional, four executions.
- Stock borrow: a flat 5% p.a. on the $1 short notional for the calendar days held.
- Reported net return = net P&L / $2 initial gross exposure. It is not a return on margin or
  unknown equity.
- SPY is a rough dollar market comparison, not a beta or sector hedge. Funding, actual borrow
  availability, variable borrow costs, taxes and slippage beyond the flat cost rate are missing.

**A positive result proves neither causation nor tradable alpha.** It specifically lacks a
comparison with contemporaneously available news, weather and river-gauge data. Stock prices can
react for many other reasons. No internal machine damage or confirmed operational interruption is
inferred from satellite imagery. Supplier relationships are not invented or placeholder-entered.

## Files

- `app.py`: local HTTP server, CSV/JSON export, parameter validation.
- `model.py`: raster processing, water detection, site exposure/severity, the duration-recession
  heuristic, later-scene evaluation.
- `watch.py`: loads and summarizes the archived news/weather alert timeline.
- `market.py`: reproducible price download, real pre-event company financials, the fixed trading
  rule, hypothetical outcome accounting.
- `fetch_data.py`: API queries and spatial downloads; resumes existing image crops.
- `web/index.html`: local UI, interactive map, news/weather timeline, duration panel, reveal flow,
  outcome chart.
- `data/`: real imagery, OSM, market data, and the manually curated, individually cited
  `watch_feed.json`, `duration_reference.json` and `company_financials.json`.
- `tests/test_core.py`: numerical checks, data integrity, future-scene separation, duration-
  estimate bounds, cost accounting.
- `analysis.json`, `validation.json`, `event_study.json`, `watch_feed_summary.json`: pre-computed
  results with starting parameters.

## Recompute, re-download data, and test

```bash
# Recompute the pre-built results
python app.py --export

# Run tests against the bundled data
python -m unittest discover -s tests -v

# Fully re-download the imagery/OSM/market data (needs internet)
python fetch_data.py --force

# Re-download only the prices
python market.py

# Use a different local port
python app.py --port 8766
```

The archived data enables a stable offline demo. Re-downloads depend on the reachability,
availability and rate limits of the external APIs. Yahoo Finance is not a contractually
guaranteed market data feed. On error, the download aborts; no synthetic substitute data is ever
generated. `watch_feed.json`, `duration_reference.json` and `company_financials.json` are not
re-downloaded by any script — they are small, manually curated facts, each citing its own public
source; update them by hand if a new event replaces this case study.

## Next sensible research step

Pre-register several events and regions, capture contemporaneous news/weather/gauge data with
their publication timestamps, independently label actual interruptions, and then compare the same
forecast with and without imagery. Only then can the original question — whether satellite
information is actually necessary — be answered with any rigor. The duration heuristic in
particular should be replaced with a model calibrated across many recession curves, not
extrapolated from a single interval of a single event.

## Data rights

Contains modified Copernicus Sentinel data 2024; see [Copernicus rights](https://www.copernicus.eu/en/access-data/copyright-and-licences).
© OpenStreetMap contributors, [ODbL 1.0 / attribution](https://www.openstreetmap.org/copyright).
OSM extracts remain ODbL-licensed. Price data is bundled for this local demonstration; publishing
or redistributing it is subject to the data provider's terms, in particular no blanket open-data
license is implied. News/weather and financial facts in `data/watch_feed.json`,
`data/duration_reference.json` and `data/company_financials.json` are factual citations to public
reporting, each with its own source link; see those sources for their own terms. Application code
is MIT licensed (see LICENSE).
# FloodAlpha
