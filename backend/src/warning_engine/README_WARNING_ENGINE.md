# Aervia Layer 4 — Warning Engine (prototype)

Converts Layer 3B event/recovery/exposure outputs into explainable, rule-based warning records. This is an operational triage prototype, **not** an official AQI implementation, medical-risk model, or pollution-source classifier.

## Files

- `src/warning_engine/config.py`: configurable prototype thresholds.
- `src/warning_engine/engine.py`: warning classification, confidence downgrades, lifecycle labels, explanations, and provenance fingerprint.
- `scripts/run_warning_engine.py`: CLI; writes `warnings.json` and `warnings.csv`.
- `tests/warning_engine/test_warning_engine.py`: basic tests.

## Run

From the `backend/` directory, after Layer 3B has generated its outputs:

```bash
PYTHONPATH=. python scripts/run_warning_engine.py \
  --analytics-dir data/analytics/ft1_final_v2 \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/warnings/ft1_final_v2 \
  --dataset-id ft1_final_v2
```

`--features` is optional and is only used to carry diagnostic readiness/status fields into the warning record. It does not increase severity. The analytics directory should contain `event_detection.json`; `recovery_profile.json` and `exposure_burden.json` are optional.

## Prototype rule defaults

| Priority | Peak PM2.5 excess above baseline |
|---|---:|
| INFORMATIONAL | below 15 µg/m³ |
| WATCH | 15 to below 30 µg/m³ |
| ELEVATED | 30 to below 75 µg/m³ |
| SEVERE | 75 µg/m³ or above |

An event lasting at least 3 minutes increases its numeric priority score by 10. Coverage below 70% downgrades confidence and labels the result `DEGRADED_CONFIDENCE`. A capture-end event is marked `OPEN_AT_CAPTURE_END`, not as a confirmed currently active live warning.

These values are prototype heuristics, not validated health thresholds. Tune them after observing the end-to-end demo. The engine does not infer source attribution, campus-wide exposure, personal dose, or medical advice. Gas and particle-distribution features do not raise severity because their interpretation is not validated in the current dataset.

## Test

```bash
PYTHONPATH=. python -m unittest discover -s tests/warning_engine -v
```