# Flood Alpha V2

Runnable Python prototype with its own trained water classifier, historical reference, and transparent model validation.

**New:** six Sentinel-2 bands, 16 spectral features, separate calibration, and testing on fully held-out country events. The additionally trained temporal candidate was rejected after poor later-period performance; persistence remains the active forecasting rule.

- [Model results and limitations](MODELLBERICHT.md)
- [Method, data, training, and reproduction](README_V2.md)
- [Original V1 state](README_V1.md)

## Getting started

Recommended: Python 3.12–3.14. In the unpacked `flood_alpha` folder:

```bash
bash run.sh
```

Alternatively:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Windows: use `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

Browser: http://127.0.0.1:8765

The first library installation requires internet access. After that, the bundled demo runs fully offline. No API keys and no external map tiles.

## Interface

The map offers current water detection, water scores, uncertainty, the old V1 rule, and the disclosed day-15 forecast. The later observation and forecast error are shown only after the reveal. The rejected temporal forecast is explicitly flagged in the evaluation.

The model validation distinguishes classification performance on reference labels from later water-forecast metrics. The site and trading rules remain traceable heuristics, not trained operational or price forecasts.

## Tests

```bash
python -m unittest discover -s tests -v
python app.py --export
```

The package includes trained models, sample data, and caches. Historical raw imagery beyond the three demo scenes is omitted from the download package and can be re-fetched if needed with `python prepare_v2.py series`. The project folder contains the full downloaded research state.

Licenses and sources: see README_V2.md and LICENSE. Application code MIT; source data retains its respective rights.
