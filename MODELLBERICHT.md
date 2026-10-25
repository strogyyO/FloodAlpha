# Model Report V2

**Result:** Water classification improves on held-out reference events. The separately trained temporal candidate fails the later check and is not approved as the default. The active forecasting rule remains persistence.

## Water classification

| Method | F1 | Precision | Recall |
|---|---:|---:|---:|
| V1: MNDWI > 0.15 | 84.72% | 99.70% | 73.66% |
| MNDWI rule optimized on validation | 89.03% | 98.98% | 80.90% |
| Custom trained classifier | 93.66% | 97.98% | 89.72% |

86 reference chips, 423,699 sample pixels; 80,000 test pixels from the fully held-out country events Bolivia and USA. Clear, homogeneously annotated 20 m blocks. No field measurements; expert-post-processed labels may contain index bias. No test of the full Brazil flood map.

| Test event | Learned classifier F1 | V1 rule F1 |
|---|---:|---:|
| Bolivia | 94.13% | 84.95% |
| USA | 91.62% | 83.74% |

## Temporal forecast: negative result stays visible

The extended fit uses 21 historical training pairs and 10 validation pairs. Fitting and threshold selection do not use the May/June target maps.

| Check | Temporal candidate F1 | Persistence F1 |
|---|---:|---:|
| Historical validation | 80.82% | 52.82% |
| May development case, May 6–21 | 4.70% | 81.73% |
| Additional pair, June 2–22 | 15.19% | 91.05% |

**Decision:** Reject the candidate. All of the candidate's values remain in the JSON report. The later checks serve the release decision, not a retroactive adjustment of model weights or thresholds. No unbiased estimate of a newly selected trading strategy is claimed.

The training pairs have at most 6.08% currently detected new water pixels in the samples. In the May case it is 17.75%. This illustrates the substantially different event size; it does not by itself prove the cause of the failure.

Even with more image pairs, a temporal model is not automatically better. The May/June situations are not sufficiently represented by the historical pairs. Future precipitation and hydraulic boundary conditions are missing. A general statement about all flood events would not be justified.

The temporal target maps are proxy labels from the frozen water classifier. The classification F1 above and the temporal F1 in this table are different tasks and must not be compared with each other. The UI additionally applies spatial-contiguity filters to its maps, so its pixel metrics may differ slightly from the raw proxy values here.

## Active in the application

- Trained water classifier and separate calibration.
- Historical reference from 13 images preceding the forecast timestamp.
- Uncertainty layer and comparison with the V1 rule.
- Site exposure and current/forecast areas shown separately.
- Persistence as the approved forecasting rule, rejected temporal candidate transparently documented.
- The historical AGCO/SPY calculation remains a hypothetical case study, not a learned price strategy.

Details and reproduction: README_V2.md.
