# Aervia Reporting Module — Layer 6

## Purpose

The reporting module composes existing Aervia outputs into a reproducible report. It consumes:

- Layer 3A parameter features (`features.csv`)
- Layer 3B analytics JSON files
- Layer 4 warning output (`warnings.json`)
- Layer 5 advisory output (`advisories.json`, optional)

It does not independently detect events, recalculate warning severity, infer missing measurements, or make causal claims.

## Files

```text
backend/
├── src/reporting/
│   ├── __init__.py
│   ├── config.py
│   ├── aggregator.py
│   ├── report_builder.py
│   └── pdf_exporter.py
├── scripts/run_report.py
├── tests/reporting/test_reporting.py
└── README_REPORTING.md
```

## Requirements

Run commands from the `backend/` directory. The module uses the project's existing Python environment and dependencies, including pandas.

PDF export is optional and requires ReportLab:

```bash
pip install reportlab
```

JSON, CSV, and HTML export do not require ReportLab.

## Generate a report

```bash
PYTHONPATH=. python scripts/run_report.py \
  --analytics-dir data/analytics/ft1_final_v2 \
  --warnings data/warnings/ft1_final_v2/warnings.json \
  --advisories data/advisories/ft1_final_v2/advisories.json \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/reports/ft1_final_v2/daily \
  --dataset-id ft1_final_v2 \
  --type daily
```

Expected outputs:

```text
data/reports/ft1_final_v2/daily/
├── report.json
├── report.html
└── warnings.csv
```

Add `--pdf` to produce `report.pdf` as well.

Optional arguments:

- `--audience operator|admin|technical`
- `--no-advisories`
- `--no-environmental-context`
- `--no-data-quality`

The current version primarily controls the audience metadata and whether selected source information is included; it does not yet produce substantially different layouts per audience.

## Report types and time windows

Supported `--type` values are:

- `event`
- `hourly`
- `daily`
- `weekly`
- `custom`

For exact time filtering, pass UTC bounds:

```bash
PYTHONPATH=. python scripts/run_report.py \
  --analytics-dir data/analytics/ft1_final_v2 \
  --warnings data/warnings/ft1_final_v2/warnings.json \
  --advisories data/advisories/ft1_final_v2/advisories.json \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/reports/ft1_final_v2/custom \
  --dataset-id ft1_final_v2 \
  --type custom \
  --start-utc 2026-10-09T09:00:00Z \
  --end-utc 2026-10-09T10:00:00Z
```

`custom` requires both bounds. The current implementation treats `event`, `hourly`, `daily`, and `weekly` as report labels; it does **not** automatically resolve calendar boundaries. Without explicit bounds, it summarizes the records present in the supplied files. A partial sensor capture must not be described as a complete day or week.

## Input files

The analytics directory may contain:

```text
event_detection.json
recovery_profile.json
exposure_burden.json
activity_association.json
intervention_check.json
```

The runner also accepts the Layer 4 warnings JSON, optional Layer 5 advisories JSON, and optional Layer 3A features CSV.

The loader supports common top-level list keys such as `warnings`, `advisories`, `events`, `records`, `integrals`, and `results`. Because schemas may evolve, inspect the report's `source_statuses` and record counts after each run.

## Report contents

The JSON report includes:

- Report ID/version, dataset ID, generation timestamp, report type, and selected window
- Warning count and count by severity
- Advisory and detected-event counts
- Maximum PM2.5 and peak excess among warnings
- Feature coverage summary, when enabled
- Warning and advisory records
- Status and records from the five analytics modules
- Input-path provenance and limitations

HTML provides a readable report and can be printed to PDF from a browser. CSV currently exports warning records, not every analytics table. JSON is the most complete output.

## Data interpretation and limitations

- Warning severity is copied from Layer 4; this module does not recalculate it.
- Missing values remain missing. The module does not interpolate measurements or invent timestamps.
- The current prototype uses one monitoring node and a limited capture window. It cannot establish campus-wide air quality or pollution source.
- Rule-based warning levels are prototype triage categories, not official AQI categories or medical thresholds.
- Concentration-time integrals are not personal inhaled dose or population exposure.
- Activity association requires synchronized activity/context data.
- Intervention analysis requires intervention records. Missing context should remain visibly unavailable or not run.
- VOC/NOx sensor indices are not calibrated gas concentrations. A `NOT_READY` state does not establish that gases are absent or safe.
- Recovery output may be partial if post-event observations are insufficient or do not support a decay fit.

## Current prototype validation notes

The sample run for `ft1_final_v2` produced:

- 4 warnings: 2 `SEVERE`, 2 `ELEVATED`
- 4 advisories
- 4 detected events
- Feature rows: 99, with 80 analysis-eligible rows (about 80.8%)
- Gas-ready rows: 0
- Recovery profile status: `PARTIAL`
- Activity association: `INSUFFICIENT_CONTEXT_DATA`
- Intervention check: `NOT_RUN`

The source feature range was **2026-10-09 08:54–10:32 UTC** (14:24–16:02 IST). The report was labelled `daily`, but its `window.start_utc` and `window.end_utc` were null. This is a partial capture, not a complete 24-hour daily report. For a defensible daily report, run against a complete 24-hour dataset and supply explicit bounds after calendar-window handling is implemented.

The generated HTML currently displays a dash for warning summaries because the report builder expects a `summary` field on warning records, while the Layer 4 records shown in the sample do not provide it. This is a presentation issue, not a failure of warning generation. A follow-up improvement is to use the linked Layer 5 advisory summary by `warning_id`/`event_id`, or provide a concise deterministic fallback.

## Tests

From `backend/`:

```bash
PYTHONPATH=. python -m pytest tests/reporting -q
```

Review the generated `report.json` and `report.html` after tests. Tests verify basic report construction and explicit custom-window filtering; they do not certify sensor calibration, scientific validity, production readiness, or scheduler behavior.

## Deliberately deferred

- Automated hourly/daily/weekly scheduling
- Calendar-boundary resolution and timezone-specific report windows
- Separate audience-specific report layouts
- Full analytics tables in CSV/PDF
- Trend comparisons across multiple days/weeks
- Dashboard/API integration and delivery notifications

Scheduling should be added after continuous ingestion and reliable time-window handling are in place.