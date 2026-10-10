# Aervia Layer 3A — Parameter Intelligence

Layer 3A derives quality-aware, parameter-specific features from Aervia's preprocessed sensor data. It is an offline feature-engineering layer: it does **not** emit warnings, provide medical advice, or independently identify pollution sources.

## Modules

- `src/parameter_intelligence/particulate.py` — PM trends, baseline excess, and cautious differences between PM channels.
- `src/parameter_intelligence/particle_distribution.py` — trends for NC particle-count channels. It does **not** derive size-bin counts until firmware documentation confirms the channel semantics.
- `src/parameter_intelligence/gas_diagnostics.py` — SGP41 readiness and index diagnostics. VOC/NOx indices are not treated as calibrated gas concentrations.
- `src/parameter_intelligence/environmental_context.py` — temperature, humidity, and pressure context. It does not correct or overwrite PM readings.
- `src/parameter_intelligence/feature_pipeline.py` — feature orchestration and manifest generation.
- `scripts/run_parameter_intelligence.py` — offline command-line runner.

## Run

Run from `backend/` with the project's virtual environment active and `pandas` and `numpy` installed:

```bash
PYTHONPATH=src python scripts/run_parameter_intelligence.py \
  --minute data/your_run/minute/minute.csv \
  --samples data/your_run/aligned/samples.csv \
  --output data/your_run/parameter_intelligence
```

Adjust the paths to match the actual preprocessing output directory.

`--samples` is optional. It supplies particle-count channels, raw SGP41 signals, and device states that may not be retained in the minute aggregate.

### Outputs

- `features.csv` — one output row per input minute row, with parameter-specific features.
- `manifest.json` — configuration, input/output counts, available channels, and known interpretation limitations.

## Contracts and assumptions

- `minute.csv` must contain a `timestamp` column and should contain no more than one row per timestamp. Duplicate timestamps are rejected rather than silently aggregated.
- Timestamps are normalized to UTC.
- The runner preserves the minute table's row count. Optional sample-only channels are aggregated by minute using the median. No interpolation is performed.
- The default high-humidity review threshold is 90%, configurable through the CLI. This is a diagnostic flag, not an automatic correction.
- `pm_ordering_tolerance` is a configurable tolerance in the same concentration units as the PM channels. Ordering violations beyond the tolerance are flagged invalid, not silently corrected.
- Particle-count channel semantics remain unverified. The pipeline does not subtract NC channels or label them as specific size bins.
- Gas indices are diagnostic only. The output keeps `gas_concentration_estimate_available` and `gas_health_warning_eligible` false.
- These features are descriptive. They do not establish a pollution source or an individual's health risk.

## Validation status

The initial output for `ft1_final_v2` contains 99 minute rows. Numerical validation passed for the tested invariants:

- Output row count agrees with the manifest.
- `pm2_5_excess` equals `pm2_5 - baseline_pm2_5` where both values are available; excess remains missing when the baseline is unavailable.
- The three PM channel-difference features match their arithmetic definitions and were non-negative in this dataset.
- Gas health-warning eligibility remains disabled while gas readiness is unavailable.
- Particle-count semantics remain explicitly marked unverified.
- `analysis_ok` does not bypass the existing `baseline_mature` flag.
- Timestamps parse successfully and are ordered.

The current test suite contains six tests covering row preservation and feature creation, missing optional channels, invalid negative size-band handling, gas-index interpretation, duplicate timestamps, and invalid configuration. These tests passed in the current development environment.

### Known issue: baseline maturity timing

In the current `ft1_final_v2` output, `baseline_mature` first becomes true at `2026-10-09 09:13:00 UTC`, 19 minutes after the first minute bin at `08:54:00 UTC`. At that point, `baseline_valid_count` is 19 and `baseline_coverage` is 0.95 for the configured 20-minute baseline window.

This is a known baseline-maturity timing discrepancy. It is documented rather than treated as a blocker for exploratory feature analysis. The existing checks confirm that `analysis_ok` follows the maturity flag, but they do **not** prove that the maturity flag's threshold is correct.

Until the maturity rule is reviewed and covered by a targeted regression test:

- Treat baseline-derived features as exploratory.
- Do not rely on this maturity flag to trigger production or real-time warnings.
- Do not interpret the passing numerical checks as complete scientific validation.

## Tests

Run from `backend/` with the project virtual environment active:

```bash
python -m pytest tests/parameter_intelligence/ -v
```

The current development run completed with **6 passed**.

## Scope limits

This first version is an offline feature-engineering layer. It does not call AWS, Redis, FastAPI, external APIs, databases, or trained ML models. It does not modify the existing preprocessing output. Scientific validity across other devices, sites, and operating conditions has not been established.