# Flood Alpha — runnable Python prototype with real data

Historical case study of the Canoas, Brazil flood, May 2024.

The application links real satellite imagery with historical industrial sites and roads, builds an exposure watchlist, tests a simple 15-day forecast, and runs through a fixed hypothetical stock position using real AGCO/SPY prices.

## Getting started

Python 3.10 or newer, recommended 3.12–3.14. Unpack the ZIP and in the `flood_alpha` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open in browser: **http://127.0.0.1:8765**

Windows: use the command `.venv\Scripts\activate` instead of `source`; use `python` instead of `python3` if needed.

On macOS/Linux, alternatively `bash run.sh`. The first installation requires internet access. After that, the bundled case study runs fully offline: no API keys, no external map tiles, no cloud application. The bundled data are real downloaded extracts, not simulated images.

## Three-minute demo

1. Click **Apr 21 · before**: the situation before the flood.
2. Switch to **May 6 · signal**: explore new water areas and site exposure.
3. Click a site in the table. Direct exposure and wet roads in the surrounding area are reported separately. AGCO South America is also in the list.
4. View the fixed hypothetical trading rule for AGCO. Its price outcome stays hidden for now.
5. **Fast-forward 15 days**: reveal the May 21 image, error map, forecast metrics, and the actual price trajectory.
6. Export CSV or JSON. Change parameters and explore sensitivity. After the reveal, changes are exploratory, not a new untouched test.

## Data and timing

| Component | Source | Period |
|---|---|---|
| Before image | Copernicus Sentinel-2 L2A, tile 22JDN | 2024-04-21 |
| Signal image | Copernicus Sentinel-2 L2A, tile 22JDN | 2024-05-06 |
| Later observation | Copernicus Sentinel-2 L2A, tile 22JDN | 2024-05-21 |
| Industrial sites, roads, bridges | Historical OpenStreetMap snapshot via Overpass | 2024-04-24 |
| AGCO and SPY | Yahoo Finance, daily open/close prices and dividends | April–June 2024 |
| AGCO ↔ Canoas mapping | AGCO Form 10-K 2023, SEC | published before the event |

Analysis area: 51.30°W to 51.07°W, 29.91°S to 29.74°S. Common grid: EPSG:32722, 20 m, 1114 × 945 pixels. The reflectance bands B02/B03/B04/B11 and the scene classification layer SCL are stored compressed in `data/`. The individual scenes, original STAC metadata, original OSM objects, market price responses, and SHA-256 checksums are included. No temporarily signed download URLs are stored.

Primary sources and access:

- [Planetary Computer / Sentinel-2](https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a)
- [Copernicus Sentinel-2](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2)
- [Historical Overpass queries](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#date)
- [AGCO 2023 10-K, SEC](https://www.sec.gov/Archives/edgar/data/880266/000088026624000013/agco-20231231.htm)
- The exact scene and data URLs are in `data/manifest.json` and `data/market_manifest.json`.

The archive retrieval took place when the prototype was created. Acquisition date and today's STAC metadata do not prove when a market participant could actually have received the image at the time. Historical publication and processing latencies have not been reconstructed.

## What is computed

### Water detection

MNDWI = (B03 − B11) / (B03 + B11), on reflectances with correct scaling and additive offset. The bands are brought onto a common 20 m grid. SCL classes 0, 1, 2, 3, 8, 9, 10, and 11 are excluded to mask invalid pixels, dark areas, shadows, clouds, and snow. The mask edge is expanded by two pixels.

New water pixels on May 6 simultaneously satisfy:

- valid on April 21 and May 6;
- before: MNDWI ≤ water threshold;
- on May 6: MNDWI > water threshold;
- MNDWI increase > change threshold.

Connected patches smaller than 25 pixels (1 ha) are removed. Default values: water threshold 0.15, change threshold 0.18. This is a traceable spectral heuristic, not a trained segmentation model. No invented flood-detection accuracy figure is given.

### Exposure

The OSM industrial areas are intersected with new water. OSM point objects have no documented factory polygon and are explicitly flagged as a 60 m approximation. Generic industrial areas that contain named production sites are removed to avoid some double counting; full entity resolution is not guaranteed.

Roads are rasterized with a 10 m buffer. The share of wet road pixels in the adjustable site surroundings is an indicative check value. Bridges and tunnels are excluded. There is **no** traffic-flow analysis and **no** proof of missing alternative routes.

Exposure index = 70 × directly exposed area share + 30 × wet road share. Sites with less than 80% valid area coverage are not scored. This index is not a calibrated failure probability.

### Real forward forecast with a simple model

The persistence approach, frozen on May 6, predicts: newly detected water areas remain wet on May 21. The future dataset is not used in the forecast or the site ranking; that is what is being tested. Only the evaluation accesses it.

F1, precision, recall, and IoU are computed only on pixels valid in all three images that were previously dry. The baseline method is "no new water area." This is deliberately a weak baseline. A meaningful weather/gauge comparison is still missing.

The May 21 reference comes from the **same sensor and the same water index**. It is a later observation, not independent ground truth. The metrics evaluate water persistence, not operational disruption. It is a single spatially contiguous event; pixels are not independent test cases.

### Hypothetical trading rule with real prices

The AGCO OSM area `way/475623590` is matched to the Canoas site based on the name and the location documented in the SEC company filing. This mapping is manually curated, not an automatic global company resolution.

Hard-coded demonstration rule: ≥5% direct area exposure or ≥10% wet road surroundings → short AGCO and long SPY with 1 USD initial notional each; otherwise no position. No order is sent. Entry on May 7, 2024 at the open, exit on May 21 at the close. Period, instruments, and thresholds form a retrospectively designed case study, not a pre-registered trading test.

- Share counts are calculated from the price at entry and are not reweighted daily.
- Cash dividends between entry and exit are credited or charged as a short liability; no reinvestment.
- Transaction costs: 10 basis points per execution on the initial notional, four executions.
- Stock borrow: flat 5% p.a. on 1 USD short notional for the calendar days held.
- Displayed net return = net P&L / 2 USD initial gross exposure. It is not a return on margin or unknown equity.
- SPY is a rough dollar market comparison, not a beta or sector hedge. Financing, actual borrow availability, variable borrow costs, taxes, and slippage beyond the flat cost rate are not included.

**A positive result proves neither causality nor tradable alpha.** In particular, a comparison with contemporaneously available news, weather data, and river gauges is missing. Stock prices can react for many other reasons. No internal machine damage or confirmed operational disruption is inferred from satellite imagery. Supplier relationships are not invented or entered as placeholders.

## Files

- `app.py`: local HTTP server, CSV/JSON export, parameter validation.
- `model.py`: raster processing, water detection, site analysis, later evaluation.
- `market.py`: reproducible price download, fixed trading rule, hypothetical outcome calculation.
- `fetch_data.py`: API queries and spatial downloads; resumes existing image extracts.
- `web/index.html`: local interface, interactive map, future reveal, results chart.
- `data/`: real data, metadata, and provenance.
- `tests/test_core.py`: numerical checks, data integrity, future-data separation, and cost calculation.
- `analysis.json`, `validation.json`, `event_study.json`: precomputed results with default parameters.

## Recompute, download data, and test

```bash
# Recompute prepared results
python app.py --export

# Tests with bundled data
python -m unittest discover -s tests -v

# Fully re-download data (internet required)
python fetch_data.py --force

# Re-download only prices
python market.py

# Use a different local port
python app.py --port 8766
```

The archived data enable a stable offline demo. Re-downloads depend on the reachability, availability, and limits of the external APIs. Yahoo Finance is not a contractually guaranteed market data feed. On error, the download aborts; no synthetic substitute data is generated.

## Next sensible research step

Pre-register several events and regions, secure contemporaneous news/weather/gauge data along with their publication timestamps, independently label actual disruptions, and then compare the same forecast with and without imagery data. Only then can the original question of necessary satellite information be answered robustly.

## Data rights

Contains modified Copernicus Sentinel data 2024; see [Copernicus rights](https://www.copernicus.eu/en/access-data/copyright-and-licences). © OpenStreetMap contributors, [ODbL 1.0 / attribution](https://www.openstreetmap.org/copyright). OSM extracts remain ODbL-licensed. Price data is included for this local demonstration; publication or redistribution is subject to the data provider's terms of use, in particular there is no blanket open-data license guarantee. The application code is under MIT (see LICENSE).
