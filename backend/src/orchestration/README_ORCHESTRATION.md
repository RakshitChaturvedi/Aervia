# Aervia Pipeline Orchestration

## Purpose

This module coordinates the existing command-line runners for the current offline pipeline:

```text
Preprocessed minute.csv + aligned samples.csv
                     |
                     v
        Layer 3A: Parameter Intelligence
                     |
               features.csv
                     |
                     v
        Layer 3B: Analytics Modules
                     |
              analytics/*.json
                     |
                     v
          Layer 4: Warning Engine
                     |
                 warnings.json
                     |
                     v
          Layer 5: Advisory Engine
                     |
                advisories.json
                     |
                     v
          Layer 6: Report Generation
              report.json/html/csv
```

Layer 3B consumes the feature output from Layer 3A in this prototype. The orchestrator therefore runs the existing runners sequentially in dependency order.

## Important scope boundary

The orchestrator begins **after preprocessing**. It requires `minute.csv` and aligned `samples.csv`; it does not start MQTT ingestion, replay, or preprocessing. Those entry points differ by environment and are intentionally not guessed or invoked. The existing preprocessing/replay pipeline should produce these inputs first.

## Run

Run from the `backend/` directory:

```bash
PYTHONPATH=. python scripts/run_pipeline.py \\
  --minute data/processed/ft1_final_v2/minute/minute.csv \\
  --samples data/processed/ft1_final_v2/aligned/samples.csv \\
  --dataset-id ft1_final_v2 \\
  --run-root data/pipeline_runs/ft1_final_v2 \
  --disable-llm
```

`--disable-llm` makes Layer 5 use deterministic advisory wording. Omit it if the existing advisory configuration should control LLM use.

Output layout:

```text
data/pipeline_runs/ft1_final_v2/
├── parameter_intelligence/
├── analytics/
├── warnings/
├── advisories/
└── reports/
    └── daily/
```

The script stops on the first failed command (`subprocess.run(..., check=True)`) so downstream layers do not consume stale or missing outputs.

## Dry run

Check the command plan without executing layers:

```bash
PYTHONPATH=. python scripts/run_pipeline.py \\
  --minute data/processed/ft1_final_v2/minute/minute.csv \\
  --samples data/processed/ft1_final_v2/aligned/samples.csv \\
  --dataset-id ft1_final_v2 \\
  --run-root data/pipeline_runs/ft1_final_v2 \\
  --dry-run
```

## Report window

The report runner accepts `--report-type event|hourly|daily|weekly|custom`, `--start-utc`, and `--end-utc`. Provide explicit UTC bounds when you need a precise reporting window. The current report module does not automatically resolve calendar-day/week boundaries. Without bounds, the report summarizes the records available in the source outputs; do not describe a partial capture as a complete daily or weekly report.

## Optional stages

- `--skip-advisories`: stop after warnings and generate the report without advisory records.
- `--skip-report`: run through advisory generation but do not create a report.
- `--disable-llm`: force deterministic advisory generation.
- `--audience operator|admin|technical`: pass report audience metadata.
- `--dry-run`: print commands without running them.

## Tests

From `backend/`:

```bash
PYTHONPATH=. python -m pytest tests/orchestration -q
```

These tests verify command order, optional stages, and dry-run behavior. They do not validate sensor calibration, scientific validity, live ingestion, AWS infrastructure, or end-to-end production reliability.

## Production notes

- This is a local/offline subprocess orchestrator, not a distributed workflow scheduler.
- It does not provision cloud resources or run AWS IoT/SQS listeners.
- Use a unique `--run-root` per dataset run to avoid mixing outputs from different executions.
- For a production deployment, add run IDs, structured logs, retries only for safe/idempotent stages, artifact freshness checks, and explicit calendar-window handling before scheduling.