# Flood Alpha V2 — Modeling, Classification, and Validation

This version includes a self-trained spectral water classifier and a separately trained temporal water forecast. The original fixed rule remains in `model.py`. The active application uses `model_v2.py`.

## The model pipeline

1. Sentinel-2 L2A surface reflectances from B02/B03/B04/B08/B11/B12.
2. Common 20 m grid, valid observations, and cloud mask.
3. Custom classifier using six bands and ten spectral features.
4. Separate calibration; decision threshold set on a different validation event.
5. Historical reference built from multiple strictly earlier images.
6. New water areas as deviation from the reference, with spatial-contiguity checking.
7. Temporal model from causal image sequences; comparison and possible combination with persistence.
8. Site exposure, uncertainty, and an explicitly hypothetical trading case study.

No external model weights are used for water detection or temporal forecasting. The L2A preprocessing and scene classification still come from the Copernicus data product.

## Training reference and geographic separation

The reference is a fixed subsample of Sen1Floods11. For each available country event, up to eight chips are selected via SHA-256 ordering. Expert labels are loaded from the public dataset. The matching Sentinel-2 L2A images are separately re-fetched from Planetary Computer so that training and application use the same processing level. The L1C images bundled with the reference dataset are not used as training input.

The labels come from an optical initial classification with manual expert post-processing; they are **not independent field measurements** and may contain remaining algorithmic/analytical errors. For aggregation onto the 20 m grid, only homogeneous 2×2 label blocks are kept. Clouds, invalid pixels, and unclear labels are not interpreted as dry. For each chip, a uniformly distributed sample of up to 5,000 valid pixels is drawn. Two of the requested chips are excluded due to insufficient valid coverage; the reasons are in the reference manifest.

Fixed partitions:

| Purpose | Country events |
|---|---|
| Training | Ghana, India, Mekong, Nigeria, Pakistan, Somalia, Sri Lanka |
| Calibration | Paraguay |
| Model and threshold selection | Spain |
| Held-out classification test | Bolivia, USA |

The sample contains 86 chips and 423,699 pixels: 268,699 training, 35,000 calibration, 40,000 selection, 80,000 test. Pixels are spatially correlated; the pixel count is not the number of independent events. The full official Sen1Floods11 benchmark is not claimed.

Sources:

- [Sen1Floods11, original repository](https://github.com/cloudtostreet/Sen1Floods11)
- [Original publication, CVPR Workshops 2020](https://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.html)
- [L2A processing documentation](https://sentiwiki.copernicus.eu/web/s2-processing)

## Custom water classifier

The 16 input features are six reflectance bands, NDWI, MNDWI, NDVI, NDBI, two AWEI variants, two brightness means, green–SWIR difference, and SWIR ratio. No coordinates are used as a feature. Index formulas are explicitly implemented in `features.py`.

Two small models are trained on the reference samples:

- Histogram Gradient Boosting: 180 iterations, maximum 23 leaves, learning rate 0.07, minimum leaf size 35, L2 regularization 1.
- Extra Trees: 100 trees, maximum depth 17, minimum leaf size 12.

Each chip has equal total weight during fitting. The natural within-chip class frequency is preserved. A logistic calibrator learns the mapping from raw scores to water probabilities on Paraguay. The model and decision threshold are chosen exclusively on Spain. Only afterward are the test labels used.

Histogram Gradient Boosting was selected. On the held-out reference samples:

| Method | F1 |
|---|---:|
| Original MNDWI threshold 0.15 | 84.72% |
| MNDWI threshold optimized on Spain | 89.03% |
| Custom trained classifier | 93.66% |

The trained classifier achieves 97.98% precision and 89.72% recall. The Brier score is 0.0132, and the calibration error computed over ten score bins is 0.0096. These results evaluate the **pixel classifier on clear, homogeneously annotated reference pixels**. They are not an accuracy proof for the full post-processed Brazil flood map, the future forecast, or the trading rule.

Calibration transfer to Brazil is not guaranteed. Water scores between 0.2 and 0.8 are shown as an exploratory uncertainty layer. They are not a formal confidence interval.

## Preprocessing and reference

Reflectance correction depends on the Sentinel-2 processing baseline. Historical products before PB 04.00 have no additive offset when explicit metadata is missing; newer products get an offset of −0.1 at a scale of 0.0001. Existing `raster:bands` metadata takes precedence. A test checks this distinction.

SCL 0, 1, 3, 8, 9, 10, and 11, as well as missing/implausible reflectances, are invalid. The edge is expanded by one pixel. SCL 2 is deliberately not discarded wholesale; dark areas are handled by the spectral classifier. Topographic shadows can therefore still produce residual errors.

The reference uses valid observations between 21 and 150 days before the respective forecast timestamp. For each pixel, the median water score and the frequency of detected water observations are computed. At least two historical observations must be available. The 21-day gap is meant to prevent the ongoing flood from immediately becoming the normal reference; this is a modeling assumption, not a proven optimal value.

New water areas must exceed the chosen model threshold, deviate from the historical reference, and lie outside the reference water area. Contiguity check: at least four pixels (0.16 ha) and a core with a water score ≥0.8, or at least the chosen decision threshold. This preserves smaller clear water objects compared to V1's flat 1 ha filter. This post-processing has not been separately validated against field labels.

## Temporal forecast

The historical Canoas image sequence spans January 2023 to June 2024. Scene selection follows a fixed maximum tile cloud cover and minimum time spacing; the full selection and failures are listed in the series manifest. Low tile cloud cover does not guarantee a cloud-free subarea. All features respect the local validity mask.

Temporal features: current and previous water score, daily change, historical reference, historical water frequency, deviation from normal, local water scores, distance to water/dry areas/reference water, forecast horizon, time since last image, and season. There is no future interpolation and no use of weather observed later.

The temporal model is a small Histogram Gradient Boosting classifier. The target value is the later water classification from the frozen spectral model. These are **proxy labels**, not independent reference observations of a flood or operational disruption.

- Training: historical image pairs up to October 2023.
- Validation: November 2023 to March 2024.
- Horizons during training: 10–20 days, nearest available pair at 15 days.
- Fixed candidates for blending with persistence: 0%, 25%, 50%, 75%, 100% temporal-model share. Weight and threshold are chosen exclusively on the historical validation data.
- The active method remains persistence if it wins on validation, or if the chosen temporal candidate fails the later release check.

The first experiment had only two usable training pairs. It beat persistence on validation but lost on the May case study. This finding is preserved in `artifacts/forecast_report_initial.json`. The earlier image history was subsequently extended. **The May case study is therefore an already-examined development case, not an untouched final test of the extended version.** It remains excluded from fitting and historical selection.

The additional image pair from June 2 to June 22, 2024 was fixed as a final temporal check before the extended training. It covers the same region and the aftermath of the same flood. This pair, too, does not demonstrate generalization to independent regions or flood events. The results are in `artifacts/forecast_report.json` and `MODELLBERICHT.md`.

The "day 15" map shows the May 6 forecast for May 21. "Forecast error" compares it with later proxy water maps. The application also shows current and forecast site areas separately. The site exposure index and the AGCO/SPY rule remain deliberately explicit heuristics; no learned probability of an operational disruption is claimed.

## Reproducing

Python 3.12–3.14 recommended. The bundled sklearn artifact state requires scikit-learn 1.9.1. Model weights are loaded locally with Joblib; only load your own or trusted artifacts.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

For model building:

```bash
# Reference labels and matching L2A image data
python prepare_v2.py benchmark --chips-per-event 8
python train_classifier.py

# Historical image sequence and causal forecast
python prepare_v2.py series
python train_forecast.py

# Tests and exported results
python -m unittest discover -s tests -v
python app.py --export
```

The download package includes the runtime data, model artifacts, reference samples, temporal-model training samples, and precomputed water scores. Historical raw imagery beyond the three demo scenes may be missing to limit package size and is re-fetched by `prepare_v2.py series`. The full research state in the project folder includes it. Probability caches are checked via the classifier's SHA-256 hash and recomputed after a changed classifier.

`requirements-lock.txt` documents the versions used here. Small numerical deviations when refitting on other platforms are possible.

## Limitations we still need to examine

- Independent, temporally matched reference polygons for the Brazil cases.
- More fully independent temporal test events and regions.
- Uncertainty and calibration within built-up industrial areas.
- Benefit relative to weather, gauges, and contemporaneous news.
- Actual disruption, restart, and market data as separate target variables.

The application and our own model scripts are under MIT. Copernicus, OSM, reference labels, and stock prices retain their respective rights and terms. The reference repository makes the data publicly available and requires scientific citation; a comprehensive redistribution license for all derived reference files has not been verified here.
