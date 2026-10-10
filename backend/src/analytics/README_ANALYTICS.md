# Aervia Layer 3B — Analytics Modules

Layer 3B consumes Layer 3A features and returns structured descriptive analytics. It makes no warnings or medical recommendations and uses no trained ML models in this version.

## Modules

- **Event Detection:** baseline-relative PM2.5 excess, persistence, configurable gap tolerance, coverage and boundary flags. Particle-distribution features are supporting evidence only.
- **Recovery Profile:** observed time to sustained return below a threshold and guarded exponential-decay fit with sample-count, dynamic-range, slope and R² checks.
- **Exposure Burden:** trapezoidal integration of total PM2.5, baseline, and positive excess over adjacent eligible observations. Long gaps are excluded.
- **Activity Association:** descriptive PM2.5 statistics during explicitly supplied activity intervals. Missing context returns `INSUFFICIENT_CONTEXT_DATA`.
- **Intervention Check:** pre/post descriptive comparison for explicitly supplied interventions. Missing intervention records return `NOT_RUN`.

## Run

From `backend/`:

```bash
python -m pytest tests/analytics/ -v
PYTHONPATH=. python scripts/run_analytics.py \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/analytics/ft1_final_v2 \
  --dataset-id ft1_final_v2
```

Optional activity CSV columns: `activity,start_utc,end_utc`.

Optional intervention CSV columns: `intervention_id,intervention,start_utc,end_utc`.

## Shared result contract

Every result contains status (`OK`, `PARTIAL`, `INSUFFICIENT_DATA`, `INSUFFICIENT_CONTEXT_DATA`, `NOT_RUN`, `FAILED_VALIDATION`), units, UTC time range, coverage, provenance (dataset ID, configuration, algorithm version, row counts, exclusions and input fingerprint), module results, limitations and valid outputs.

## Provisional defaults

- Event excess threshold 15 µg/m³; persistence 2 candidate observations; gap tolerance 1 minute.
- Recovery excess threshold 5 µg/m³ for 3 consecutive contiguous eligible minutes; 60-minute follow-up window.
- Decay fitting requires at least 8 positive observations, dynamic range >= 2 µg/m³, a negative fitted slope, and R² >= 0.70.
- Exposure integration rejects gaps longer than 2 minutes.
- Intervention comparison uses 10-minute pre/post windows and at least 5 eligible observations per window.

These are provisional exploratory defaults, not scientifically validated thresholds. Adjust through configuration and document rationale.

## Limitations

- Baseline-derived outputs inherit the known Layer 3A baseline-maturity timing discrepancy. Treat results as exploratory until it is reviewed.
- Events touching capture boundaries may be censored.
- Concentration-time integral is not personal inhaled dose or population exposure.
- Activity overlap is descriptive; before/after differences do not prove causality.
- The short, single-gate capture does not establish campus-wide conditions or generalization to other sites.