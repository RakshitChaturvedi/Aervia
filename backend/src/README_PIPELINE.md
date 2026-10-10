# Aervia Backend Source Architecture (`README_PIPELINE.md`)

## 1. Purpose and scope

This document explains the Aervia backend prototype from incoming sensor data through ingestion, preprocessing, parameter intelligence, analytics, warnings, advisories, reporting, and orchestration.

The current implementation is a **local, file-based analytical pipeline**. It has been exercised against the `ft1_final_v2` capture. The complete orchestrated run succeeded, and the backend test suite reported **56 passed**.

This document describes the implemented prototype and its current constraints. It does not claim that every analytical threshold is scientifically validated or that the system is production-ready.

### What the pipeline does

1. Accepts sensor messages or replays previously collected data.
2. Preserves raw input and records ingestion/quality outcomes.
3. Normalizes records and creates aligned sample, minute, and other processed datasets.
4. Derives parameter-level features from PM, particle-count, gas-index, and environmental channels.
5. Runs five analytics modules.
6. Converts eligible detected events into rule-based warnings.
7. Generates deterministic or optional LLM-assisted advisories.
8. Aggregates the outputs into report artifacts.
9. Runs the stages in dependency order through one orchestration command.

### Important scope boundaries

- One sensor node represents its own sampling location, not an entire campus, city, or region.
- A detected PM episode is not proof of its source.
- Integrated PM excess is not personal inhaled dose or population exposure.
- The current warning thresholds are provisional prototype rules, not official Indian AQI or medical thresholds.
- VOC and NOx **index** readings are not calibrated gas concentrations.
- Gas interpretation is unavailable for the current capture because no rows are marked gas-ready.
- Particle-count channel semantics have not yet been independently verified; size-bin arithmetic must not be treated as validated until that contract is confirmed.
- Activity association and intervention evaluation require synchronized context records. The current run does not have them.
- The known Layer 3A baseline-maturity timing discrepancy remains to be fixed before real-time alerting or validated conclusions.

---

## 2. High-level architecture

```text
Sensor / recorded capture
          |
          v
  Ingestion and replay
  - parse incoming records
  - validate/map fields
  - preserve raw payload
  - handle duplicates and invalid records
          |
          v
  Preprocessing
  - normalize timestamps and channels
  - retain untimestamped records without inventing time
  - apply quality flags
  - align samples
  - aggregate to minute bins
  - compute causal PM baseline and excess
          |
          v
  Layer 3A: Parameter Intelligence
  - PM trends and rolling features
  - PM size-band diagnostics
  - particle-count features
  - gas readiness / index diagnostics
  - temperature, humidity, pressure context
          |
          v
  Layer 3B: Analytics Modules
  ├── Event Detection
  ├── Recovery Profile
  ├── Exposure Burden
  ├── Activity Association
  └── Intervention Check
          |
          v
  Layer 4: Warning Engine
  - apply configurable rule thresholds
  - check event eligibility and coverage
  - assign warning severity and lifecycle state
          |
          v
  Layer 5: Advisory Engine
  - build evidence-bounded context
  - choose approved deterministic actions
  - optionally generate language with an LLM
  - validate generated output
          |
          v
  Layer 6: Report Generation
  - aggregate analytics, warnings, advisories
  - export JSON, HTML, CSV, optional PDF
          ^
          |
  Orchestration runs each stage in order and
  passes the correct artifact paths between them.
```

The layer labels describe the analytical pipeline. Ingestion and preprocessing are upstream data foundations; Layers 3A–6 perform feature derivation, analysis, warning, advisory, and reporting.

---

## 3. Repository layout

Paths below are relative to the `backend/` directory.

```text
backend/
├── src/
│   ├── ingestion/
│   │   └── ...                 # message parsing, mapping, persistence/replay support
│   ├── preprocessing/
│   │   └── ...                 # normalization, quality, aggregation, baseline
│   ├── parameter_intelligence/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── particulate.py
│   │   ├── particle_distribution.py
│   │   ├── gas_diagnostics.py
│   │   ├── environmental_context.py
│   │   └── feature_pipeline.py
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── common.py
│   │   ├── config.py
│   │   ├── event_detection.py
│   │   ├── recovery_profile.py
│   │   ├── exposure_burden.py
│   │   ├── activity_association.py
│   │   ├── intervention_check.py
│   │   └── runner.py
│   ├── warning_engine/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── engine.py
│   ├── advisory/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── context_builder.py
│   │   ├── rules.py
│   │   ├── llm_generator.py
│   │   ├── validator.py
│   │   └── engine.py
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── aggregator.py
│   │   ├── report_builder.py
│   │   └── pdf_exporter.py
│   └── orchestration/
│       ├── __init__.py
│       └── pipeline.py
├── scripts/
│   ├── ...                      # ingestion/preprocessing utilities
│   ├── run_parameter_intelligence.py
│   ├── run_analytics.py
│   ├── run_warning_engine.py
│   ├── run_advisory_engine.py
│   ├── run_report.py
│   └── run_pipeline.py
├── tests/
│   ├── ingestion/
│   ├── preprocessing/
│   ├── parameter_intelligence/
│   ├── analytics/
│   ├── warning_engine/
│   ├── advisory/
│   ├── reporting/
│   └── orchestration/
├── data/
│   ├── collected/
│   ├── processed/
│   └── pipeline_runs/
├── .env.example
└── ...
```

The exact ingestion/preprocessing file inventory can vary as those modules evolve. The layer-specific files above describe the current analytical modules and their runner entry points.

---

## 4. Ingestion: getting sensor records into the backend

### 4.1 Input paths

The backend can work with live sensor messages or recorded data replayed through the ingestion path. For the current prototype, replay is useful because it makes the pipeline repeatable without requiring the physical device to be connected.

The ingestion layer is responsible for turning an incoming record into a normalized internal sensor record while retaining the original payload for traceability.

Typical responsibilities include:

- parsing JSON or supported replay exports;
- mapping device fields to the backend's internal schema;
- validating field types;
- preserving payloads that cannot be fully interpreted;
- distinguishing invalid records from duplicate records;
- handling boot/session identifiers when deciding whether a sequence number is a duplicate;
- retaining records with unsynchronized or missing timestamps without fabricating wall-clock time;
- recording ingestion outcomes so that malformed input does not silently disappear.

### 4.2 Validation and preservation rules

A malformed field must not be silently reassigned to a different field. For example, if a timestamp string appears in the pressure field, pressure should be quarantined/set to null and the raw row retained for review. The parser must not reinterpret the value as a timestamp unless the input contract explicitly says to do so.

A timestamp without a timezone is rejected where an aware timestamp is required. Missing timestamps can be retained as unsynchronized records when the input route supports them.

Duplicate suppression is scoped by the applicable device/boot context. A repeated sequence number after a new boot is not necessarily a duplicate of a prior boot's sequence.

### 4.3 Replay and reproducibility

Replay makes it possible to test ingestion and downstream processing against a known capture. Replay outputs are append-only in the current workflow. **Use a fresh output directory for each replay** unless intentionally testing append/deduplication behavior; replaying into an existing output directory can duplicate records.

The tests cover malformed input handling, timestamp preservation, duplicate handling, record ordering, and continuing after an invalid record.

### 4.4 Local versus future cloud path

The intended architecture can use different transports while preserving the same downstream processing contract:

```text
Local:
Sensor / export -> local MQTT or replay -> ingestion -> preprocessing -> analytics

Cloud target:
Device -> AWS IoT Core -> SQS/routing -> ingestion -> preprocessing -> analytics
```

Cloud infrastructure is not required to run the local analytical pipeline. AWS IoT, queues, storage, or notification infrastructure should be treated as separate deployment concerns, and infrastructure-changing setup scripts should not be run casually.

---

## 5. Preprocessing: turning packets into analyzable time series

Preprocessing produces consistent time-aligned data for the analytical stages. It is not merely file cleanup: its quality decisions determine which observations can be used by later analyses.

### 5.1 Main responsibilities

- normalize channel names and data types;
- parse timestamps where valid;
- preserve untimestamped rows without inventing timestamps;
- flag missing, invalid, suspicious, or unsynchronized observations;
- create aligned sample-level records;
- aggregate eligible observations into minute bins;
- preserve empty time bins as gaps rather than manufacturing readings;
- calculate a causal PM baseline and PM excess;
- identify which time bins are eligible for analysis.

### 5.2 Quality flags and eligibility

Quality diagnostics include flags such as:

- `MISSING`
- `OUT_OF_RANGE`
- `FLATLINE`
- `SPIKE`
- `RESTART`
- `SENSOR_FAULT`
- `HUMIDITY`
- `CLOCK_UNSYNCED`
- `STARTUP`
- `SOURCE_REVIEW`
- `GAP`

The exact eligibility result is represented separately from the flag itself. The code distinguishes PM eligibility, strict eligibility, timestamp quality, gas readiness, and downgraded quality. A spike is a diagnostic by default; it is not automatically discarded from exploratory PM analysis because a spike could represent a real plume or a sensor artifact. Analyses should compare results with and without spike-flagged observations when that distinction matters.

Gas readiness is separate from PM eligibility. A sample can be usable for PM analysis while not being suitable for interpreting gas-index channels.

### 5.3 Aggregation and gaps

Minute aggregation summarizes available observations for each minute. Missing minutes remain missing/gaps; the pipeline does not silently interpolate a reading into a gap. Coverage and valid counts are carried forward so downstream modules can distinguish a supported estimate from a sparse or incomplete interval.

### 5.4 Baseline and excess

The prototype uses a causal rolling PM baseline based on a rolling low quantile (default configuration: 20-minute causal 10th percentile in preprocessing). The baseline must use prior eligible information rather than future observations. PM excess is derived from observed PM2.5 relative to the baseline when the baseline is ready.

A missing or immature baseline means PM excess is unavailable for that time bin. It must not be replaced with zero.

**Known issue:** the current output has a baseline-maturity timing discrepancy: `baseline_mature` becomes true earlier than intended (about 19 minutes after the first minute bin in the reviewed capture). This is documented as a deferred bug, not accepted behavior. Fix and re-test it before relying on real-time alert timing or treating event metrics as validated.

### 5.5 Current capture summary

For `ft1_final_v2`, preprocessing produced:

- 5,910 sample records;
- 5,838 timestamped records and 72 untimestamped records;
- 99 minute bins;
- 5,850 PM-quality-eligible sample rows and 60 quality-excluded rows in the reviewed preprocessing output;
- a retained review record for the corrupt pressure field rather than silently remapping it.

The analyzed minute window is `2026-10-09 08:54 UTC` through `2026-10-09 10:32 UTC`. This is approximately 99 minutes, not a complete day.

---

## 6. Layer 3A — Parameter Intelligence

### 6.1 Purpose

Parameter Intelligence converts preprocessed channel readings into reusable, parameter-specific features. It is a shared feature layer, not the event detector or warning engine itself.

Entry point:

```text
src/parameter_intelligence/feature_pipeline.py
scripts/run_parameter_intelligence.py
```

### 6.2 Feature groups

#### Particulate matter

For the available PM channels (`pm1`, `pm2_5`, `pm4`, `pm10`), the pipeline derives features such as:

- channel availability;
- short-term change;
- rolling mean;
- rate of change;
- PM2.5 excess relative to the baseline;
- positive PM2.5 excess where applicable.

These are measurements and derived diagnostics, not source attribution.

#### PM size-band diagnostics

The pipeline calculates raw and validated differences between adjacent PM channels, such as:

- `pm1_to_pm2_5_band`
- `pm2_5_to_pm4_band`
- `pm4_to_pm10_band`

It checks whether the observed channel ordering is plausible within a configured tolerance. Invalid negative bands beyond tolerance are flagged rather than silently clipped to zero.

These differences are useful as exploratory size-band diagnostics, but their interpretation depends on sensor channel definitions and calibration. They do not identify a pollution source on their own.

#### Particle-count channels

For channels such as `nc0_5_per_cm3`, `nc1_0_per_cm3`, `nc2_5_per_cm3`, `nc4_per_cm3`, and `nc10_per_cm3`, features include availability, changes, rolling medians, relative-to-median behavior, and invalidity diagnostics.

The current manifest explicitly reports `particle_count_semantics_verified=false`. Therefore, the existence of count channels does not establish that size-bin arithmetic or physical interpretation is validated.

#### Gas diagnostics

The current input has VOC and NOx index channels. The feature layer records readiness and diagnostic state, but does **not** convert these indices into gas concentrations.

The capture's sensor states are largely learning, warm-up, or conditioning states; the output reports zero gas-ready rows. Gas interpretation and gas-based warnings therefore remain unavailable.

#### Environmental context

Temperature, humidity, and pressure availability and rolling/change features are included as contextual variables. They do not overwrite PM readings. The current implementation does not apply a PM humidity correction.

Environmental context can help explain conditions, but a contextual association is not proof of causation.

### 6.3 Output contract

The main output is:

```text
parameter_intelligence/
├── features.csv
└── manifest.json
```

The manifest records feature version, configuration, row counts, time range, available channels, gas-ready count, and important limitations.

### 6.4 Run independently

From `backend/`:

```bash
PYTHONPATH=. python scripts/run_parameter_intelligence.py \
  --minute data/processed/ft1_final_v2/minute/minute.csv \
  --samples data/processed/ft1_final_v2/aligned/samples.csv \
  --output data/parameter_intelligence/ft1_final_v2/
```

The orchestrator runs this stage automatically and writes it under the run root.

---

## 7. Layer 3B — Analytics Modules

### 7.1 Purpose and structure

Layer 3B consumes `features.csv` and runs five independent analytics modules. They share common schemas, configuration, coverage handling, provenance, and status reporting.

Entry point:

```text
src/analytics/runner.py
scripts/run_analytics.py
```

The current implementation is deterministic/statistical. It is not a collection of trained ML models.

### 7.2 Shared result semantics

Module statuses include:

- `OK` — module ran with sufficient input for its declared output;
- `PARTIAL` — a result exists, but coverage or follow-up is incomplete;
- `INSUFFICIENT_DATA` — not enough eligible measurements;
- `INSUFFICIENT_CONTEXT_DATA` — required external/context records are absent or inadequate;
- `NOT_RUN` — module was not run, or its required workflow was not activated;
- `FAILED_VALIDATION` — input or output failed a validation requirement.

Status must be read alongside the result values. An empty result set is not interchangeable with a result of zero events. Coverage, eligible counts, provenance, algorithm version, input fingerprint, and limitations are intended to make outputs auditable.

### 7.3 Module 1: Event Detection

Detects candidate PM2.5 episodes relative to the causal baseline and configured excess threshold. It checks persistence, eligible observations, gaps, and coverage.

Current exploratory defaults include:

- PM2.5 excess threshold: 15 µg/m³;
- persistence: 2 minutes;
- gap tolerance: 1 minute;
- minimum coverage: 0.70;
- minimum eligible minutes: 2.

These are configurable prototype defaults, not validated universal thresholds. Detected events are episodes in the sensor record; they do not identify the emission source.

Current capture: four candidate events were detected. The final event reaches the capture boundary, so its end/recovery is not observed in the dataset.

### 7.4 Module 2: Recovery Profile

Evaluates the behavior after an event peak and estimates when PM excess returns below a configured recovery threshold for the required consecutive minutes. It can attempt a decay fit only when there are enough observations, sufficient dynamic range, and adequate fit quality.

A recovery time is not the same as a validated physical decay constant. Sparse follow-up or a capture ending immediately after an event must be reported as incomplete rather than extrapolated as fact.

Current capture: the module status is `PARTIAL`. Some events have a threshold-based recovery time; the decay fit was not justified, and later events have insufficient follow-up or end at the capture boundary.

### 7.5 Module 3: Exposure Burden

Integrates positive PM2.5 excess over time when eligible measurements and gap constraints permit it. The output is an integral with units such as µg·h/m³.

Interpretation boundaries:

- it describes concentration excess integrated over time at the sensor location;
- it is not personal inhaled dose;
- it is not population exposure;
- it does not imply how many people were present or exposed;
- it is sensitive to baseline choice, coverage, and event boundaries.

Current capture: four event-associated integrals were produced.

### 7.6 Module 4: Activity Association

Compares air-quality features with supplied, synchronized activity/context records. It requires a context dataset with suitable timestamps and enough observations per group.

Current capture: `INSUFFICIENT_CONTEXT_DATA`. No synchronized activity records were supplied. The module must not infer activities or label a source based only on coincident PM changes.

### 7.7 Module 5: Intervention Check

Compares eligible pre- and post-intervention windows around a recorded intervention. It requires an intervention record and sufficient valid measurements in both windows.

Current capture: `NOT_RUN`, because no intervention records were supplied. Even with records, a before/after difference alone does not establish causal effect; confounding and experimental design must be considered.

### 7.8 Run independently

```bash
PYTHONPATH=. python scripts/run_analytics.py \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/analytics/ft1_final_v2 \
  --dataset-id ft1_final_v2
```

The output directory contains the module artifacts and a run manifest. Use the manifest and per-module status fields rather than assuming every module succeeded simply because the process exited normally.

---

## 8. Layer 4 — Warning Engine

### 8.1 Purpose

The Warning Engine converts eligible analytic events into operational warning records using configurable rules. It is distinct from event detection:

- **Event Detection** asks whether the measurements meet the event criteria.
- **Warning Engine** asks whether that event should be assigned a warning level and issued under the warning policy.

Entry point:

```text
src/warning_engine/engine.py
src/warning_engine/config.py
scripts/run_warning_engine.py
```

### 8.2 Inputs and outputs

Inputs:

- Layer 3B analytics output directory;
- Layer 3A `features.csv`.

Outputs include warning records, a machine-readable JSON artifact, and a run summary. Warning records retain links to the underlying event and include relevant metrics, severity, coverage/confidence information, and lifecycle state.

### 8.3 Prototype rule behavior

Current defaults include excess thresholds for watch/elevated/severe levels (15, 30, and 75 µg/m³), a minimum elevated duration, and coverage requirements. The rules also account for events whose follow-up is incomplete.

These values are prototype triage settings, not official AQI categories, health limits, or medical guidance. They must be calibrated and validated before operational use.

A warning with an open event at the end of the capture should be marked as open/incompletely followed up. The system must not imply that it has observed recovery when the capture ends first.

### 8.4 Run independently

```bash
PYTHONPATH=. python scripts/run_warning_engine.py \
  --analytics-dir data/analytics/ft1_final_v2 \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/warnings/ft1_final_v2 \
  --dataset-id ft1_final_v2
```

Current capture: four warnings were issued from four detected events. Two were labelled Elevated and two Severe under the prototype thresholds. These labels describe the configured rules, not official air-quality categories.

---

## 9. Layer 5 — Advisory Engine

### 9.1 Purpose

The Advisory Engine converts a warning plus supporting evidence into a bounded, actionable message. It is deliberately separate from the Warning Engine: severity assignment and suggested response are different responsibilities.

Entry point:

```text
src/advisory/context_builder.py
src/advisory/rules.py
src/advisory/llm_generator.py
src/advisory/validator.py
src/advisory/engine.py
scripts/run_advisory_engine.py
```

### 9.2 Processing sequence

1. Load warning records and relevant analytics/features.
2. Build a bounded context containing evidence and limitations.
3. Select actions from the approved deterministic rule set.
4. Optionally ask the configured LLM to phrase the advisory.
5. Validate the output and preserve the approved action set.
6. Use deterministic fallback behavior if LLM generation is disabled or fails.
7. Write advisory records linked to their corresponding warnings/events.

The LLM is a language-generation component, not the sensor-analysis authority. It must not invent measurements, claim unavailable gas channels are safe, add unapproved actions, or convert correlation into causal claims. The validator protects the approved action set.

### 9.3 Deterministic versus LLM mode

Deterministic mode is appropriate for repeatable local testing:

```bash
PYTHONPATH=. python scripts/run_advisory_engine.py \
  --warnings data/warnings/ft1_final_v2/warnings.json \
  --analytics-dir data/analytics/ft1_final_v2 \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/advisories/ft1_final_v2 \
  --disable-llm
```

In the orchestrated run shown for `ft1_final_v2`, all four advisories were generated in `DETERMINISTIC` mode.

LLM mode is optional and depends on a configured API key and a currently available model name. Keep credentials in the local environment file; do not commit secrets. Model identifiers can change, so verify the selected model against the provider's current API.

Example environment settings:

```dotenv
GEMINI_API_KEY=
AERVIA_ADVISORY_LLM_ENABLED=false
GEMINI_MODEL=gemini-2.0-flash
AERVIA_ADVISORY_LANGUAGE=en
AERVIA_ADVISORY_MAX_ACTIONS=4
```

The model name above is an example from the configuration template, not a guarantee that the model remains available. In the current development history, that identifier returned a 404 and had to be changed. Deterministic mode does not require an LLM API key.

### 9.4 Safety and wording constraints

- Do not describe a local sensor reading as a city-wide condition.
- Do not claim personal dose or population exposure without the relevant measurements and exposure model.
- Do not provide a source attribution unsupported by the data.
- Do not call gas conditions safe when gas readiness is unavailable.
- Keep advice proportional to the evidence and distinguish current conditions from incomplete follow-up.

---

## 10. Layer 6 — Report Generation

### 10.1 Purpose

The reporting layer assembles the outputs from analytics, warnings, advisories, and feature summaries into operator-facing artifacts.

Entry point:

```text
src/reporting/aggregator.py
src/reporting/report_builder.py
src/reporting/pdf_exporter.py
scripts/run_report.py
```

### 10.2 Inputs and outputs

Inputs can include:

- analytics output directory;
- warnings JSON;
- advisories JSON;
- parameter feature CSV;
- dataset identifier;
- report type and audience;
- optional explicit start/end time bounds.

The report generator can produce JSON, HTML, and CSV outputs, with optional PDF export when the required PDF dependency is installed. The exact set of files depends on the configuration and available data.

### 10.3 Window semantics

The report type (`daily`, `weekly`, etc.) is currently a **label**, not an automatic date-window resolver. Do not assume `--type daily` filters the data to midnight-to-midnight.

Pass explicit UTC bounds when a report must cover a specific interval. Always display the actual data window and distinguish the capture window from the requested reporting period.

For the current capture, the data window is 08:54–10:32 UTC on 2026-10-09. A report labelled `daily` without explicit bounds must not be described as a complete daily report.

### 10.4 Warning/advisory linkage

Warnings and advisories are separate artifacts. The report should join them using a stable warning/event identifier and should not depend on an optional free-text `summary` field existing in the warning record. If a warning summary is absent, either use the linked advisory summary or a deterministic fallback. Verify the rendered HTML rather than checking only that the report command exited successfully.

### 10.5 Run independently

```bash
PYTHONPATH=. python scripts/run_report.py \
  --analytics-dir data/analytics/ft1_final_v2 \
  --warnings data/warnings/ft1_final_v2/warnings.json \
  --advisories data/advisories/ft1_final_v2/advisories.json \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/reports/ft1_final_v2/daily \
  --dataset-id ft1_final_v2 \
  --type daily \
  --audience operator
```

Add the supported explicit start/end options when the reporting period must be constrained. Use `python scripts/run_report.py --help` to confirm the installed CLI's current argument names.

---

## 11. Orchestration: running the whole pipeline

### 11.1 Purpose

Orchestration is the control layer. It does not reimplement the analytics; it invokes each stage's command-line runner in dependency order, passes artifact paths, stops when a required stage fails, and groups outputs under one run root.

Entry point:

```text
src/orchestration/pipeline.py
scripts/run_pipeline.py
```

### 11.2 Dependency order

The current orchestrator runs five stages:

1. Parameter Intelligence (3A)
2. Analytics Modules (3B)
3. Warning Engine (4)
4. Advisory Engine (5)
5. Report Generation (6)

Ingestion and preprocessing are upstream prerequisites in the current run contract: the orchestrator consumes their prepared `minute.csv` and `samples.csv` inputs. It does not automatically replay raw capture data or create those preprocessing files as part of this five-stage command.

### 11.3 Artifact flow

For a run root of `data/pipeline_runs/ft1_final_v2`, the orchestrator creates a structure similar to:

```text
data/pipeline_runs/ft1_final_v2/
├── parameter_intelligence/
│   ├── features.csv
│   └── manifest.json
├── analytics/
│   ├── ... module outputs ...
│   └── ... manifest ...
├── warnings/
│   └── warnings.json
├── advisories/
│   └── advisories.json
└── reports/
    └── daily/
        └── ... report artifacts ...
```

Each stage consumes the preceding stage's files. The report stage receives the analytics directory, warnings, features, and—when enabled—the advisories JSON.

### 11.4 Run the complete pipeline

Run from the `backend/` directory:

```bash
PYTHONPATH=. python scripts/run_pipeline.py \
  --minute data/processed/ft1_final_v2/minute/minute.csv \
  --samples data/processed/ft1_final_v2/aligned/samples.csv \
  --dataset-id ft1_final_v2 \
  --run-root data/pipeline_runs/ft1_final_v2 \
  --disable-llm
```

`PYTHONPATH=.` allows imports such as `src.parameter_intelligence` to resolve when the command is launched from the backend directory.

`--disable-llm` forces deterministic advisory generation. Omit it only when you intentionally want to test the configured LLM path and have supplied valid credentials/model settings.

The current run completed all five stages:
- 3A: 99 feature rows;
- 3B: 4 detected events and 4 exposure integrals;
- 4: 4 warnings issued;
- 5: 4 deterministic advisories;
- 6: report generated with 4 warnings, 4 advisories, and 4 events.

### 11.5 Rerunning and reproducibility

The pipeline writes to the run-root subdirectories. Rerunning with the same run root will regenerate or overwrite outputs according to each runner's file-writing behavior. For a clean comparison, use a new run-root/dataset identifier or archive the previous outputs before rerunning.

For a valid comparison, preserve:
- source capture/version;
- preprocessing configuration and output;
- feature configuration and version;
- analytics/warning configuration;
- run timestamp and time window;
- generated manifests and report artifacts.

Do not combine outputs from different runs unless their dataset identifiers and input fingerprints have been checked.

### 11.6 Failure handling and CLI contracts

Each runner has its own command-line interface. Orchestration arguments must match the runner's actual CLI. For example, the advisory runner does not accept `--dataset-id`, while the report runner does. Keep orchestration commands aligned with `--help` output and add tests when runner contracts change.

A successful stage prints its summary; a failed subprocess should stop the pipeline rather than allowing downstream stages to operate on missing or stale files. After any orchestration change, run both the orchestration tests and the full suite.

---

## 12. Current run: what the numbers mean

The `ft1_final_v2` analysis covered approximately 99 minute bins from 08:54 to 10:32 UTC on 2026-10-09.

The four detected events were exploratory PM2.5 excess episodes. The final event reached the capture boundary. Four warning records and four advisories were generated from them.

These are pipeline outputs, not proof that:
- the source of any event is known;
- the event affected the whole campus or surrounding region;
- a specified number of people were exposed;
- a particular person's inhaled dose is known;
- the detected event was caused by a specific activity;
- an intervention caused an observed change;
- gas conditions were safe or unsafe based on the current index channels.

The current run's module statuses were:

| Module | Status | Interpretation |
|---|---|---|
| Event Detection | `OK` | Events found under current configured criteria |
| Recovery Profile | `PARTIAL` | Some follow-up is incomplete or insufficient for decay fitting |
| Exposure Burden | `OK` | Integrals calculated where eligible data and gap rules permitted |
| Activity Association | `INSUFFICIENT_CONTEXT_DATA` | No synchronized activity context supplied |
| Intervention Check | `NOT_RUN` | No intervention record supplied |

`OK` means the module completed under its declared contract. It does not mean that its parameters or conclusions have been independently validated.

---

## 13. Configuration and environment

- Use the project's virtual environment when available.
- Run commands from `backend/`, unless a script explicitly documents otherwise.
- Set `PYTHONPATH=.` for the current `src` import layout.
- Keep API credentials in `.env` or another secrets manager, never in source control.
- Use `.env.example` as a configuration template and verify each variable is actually consumed by the relevant module.
- Confirm model/API availability before enabling LLM generation.
- Keep local test runs deterministic by using `--disable-llm`.

Dependencies and configuration can evolve. For the authoritative current CLI arguments, use each script's `--help` output.

---

## 14. Testing

From `backend/`:

```bash
python -m pytest tests/ -v
```

The latest recorded run collected 56 tests and completed with **56 passed**. Coverage includes:

- ingestion schema mapping, validation, duplicate handling, and replay;
- timestamp preservation and malformed-record handling;
- preprocessing quality flags, aggregation, gaps, and causal baseline behavior;
- feature engineering, optional channels, and validation;
- event detection, exposure integration, recovery-fit guards, and context requirements;
- warning eligibility and coverage degradation;
- advisory action generation and validation;
- report generation and time-window filtering;
- orchestration order, optional stages, and dry-run input checks.

A passing test suite verifies the tested software behavior. It does not establish field calibration, external validity, or scientific validity of the thresholds.

---

## 15. Known limitations and next engineering work

### Required before relying on real-time warnings

1. **Correct and test baseline maturity.** Resolve the discrepancy between the intended rolling-baseline warm-up and the observed early `baseline_mature` flag.
2. **Validate event/warning thresholds.** Use more captures, documented review, and sensitivity analysis. Do not tune thresholds only to produce attractive events in one short recording.
3. **Validate time and sensor behavior.** Confirm clock synchronization, sensor warm-up, calibration, and field-specific quality characteristics.
4. **Confirm particle-count semantics.** Verify the channel definitions before interpreting size-band arithmetic.
5. **Keep gas interpretation gated.** Do not enable concentration-level gas claims without validated sensor states and calibration.

### Required for more complete analytics

6. Supply synchronized activity records for Activity Association.
7. Supply intervention timestamps and a defensible comparison design for Intervention Check.
8. Collect longer post-event periods to improve recovery estimates and avoid capture-boundary truncation.
9. Improve report window resolution and warning/advisory summary linkage.
10. Add dataset/run identifiers and input fingerprints consistently across all artifacts.

### Required before production deployment

11. Define persistence, retention, access control, secret management, and monitoring for live ingestion.
12. Validate duplicate handling and replay/idempotency behavior under the actual transport.
13. Establish failure/retry policies and observability for queues and downstream jobs.
14. Review migrations, storage contracts, and cloud infrastructure separately before enabling production services.
15. Establish a deployment-specific validation and alert escalation policy. Do not present prototype warning levels as official public-health thresholds.

---

## 16. Quick reference

| Task | Command |
|---|---|
| Run Layer 3A | `PYTHONPATH=. python scripts/run_parameter_intelligence.py --minute data/processed/ft1_final_v2/minute/minute.csv --samples data/processed/ft1_final_v2/aligned/samples.csv --output data/parameter_intelligence/ft1_final_v2/` |
| Run Layer 3B | `PYTHONPATH=. python scripts/run_analytics.py --features data/parameter_intelligence/ft1_final_v2/features.csv --output data/analytics/ft1_final_v2 --dataset-id ft1_final_v2` |
| Run Layer 4 | `PYTHONPATH=. python scripts/run_warning_engine.py --analytics-dir data/analytics/ft1_final_v2 --features data/parameter_intelligence/ft1_final_v2/features.csv --output data/warnings/ft1_final_v2 --dataset-id ft1_final_v2` |
| Run Layer 5 deterministically | `PYTHONPATH=. python scripts/run_advisory_engine.py --warnings data/warnings/ft1_final_v2/warnings.json --analytics-dir data/analytics/ft1_final_v2 --features data/parameter_intelligence/ft1_final_v2/features.csv --output data/advisories/ft1_final_v2 --disable-llm` |
| Run Layer 6 | See the full report command in Section 10.5 |
| Run full pipeline | See Section 11.4 |
| Run all tests | `python -m pytest tests/ -v` |

---

## 17. Final status

The backend prototype has a working local flow from prepared sensor data to report artifacts. The latest full run completed all five orchestrated stages, and the latest recorded test suite passed 56/56 tests.

The appropriate status is **integration-complete prototype for the current capture; analytical validation and production hardening remain**.