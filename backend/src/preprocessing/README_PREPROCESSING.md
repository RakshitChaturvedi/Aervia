# Aervia Preprocessing Pipeline

## 1. Purpose

The preprocessing layer converts raw Aervia sensor telemetry into
quality-labelled samples and time-aligned datasets that can be used for
exploratory particulate-matter (PM) event detection.

It sits between ingestion and downstream analyses. Its responsibilities
are to:

-   load replayed or collected telemetry;
-   normalize timestamps and numeric fields without fabricating missing
    values;
-   preserve source data and identify malformed or questionable records;
-   assess sample quality while keeping PM eligibility separate from
    gas-sensor readiness;
-   aggregate samples into one-minute and five-minute tables;
-   calculate a rolling PM2.5 baseline and baseline-relative features;
-   record exclusions, configuration, and output counts for
    auditability.

This pipeline does **not** establish pollution sources, personal
exposure, health effects, or causal impact. Those require additional
evidence and separately validated analyses.

## 2. Position in the data flow

``` text
Raw device telemetry / replayed JSONL
                |
                v
       scripts/preprocess_dataset.py
                |
                v
         preprocessing.io
     Read and normalize input
                |
                v
       preprocessing.quality
   Quality flags and eligibility
                |
                v
      preprocessing.aggregation
   One-minute and five-minute tables
                |
                v
        preprocessing.baseline
 Rolling PM2.5 baseline and excess
                |
                v
        preprocessing.pipeline
 Coordinate stages, exclusions,
 summary, manifest, and output files
                |
                v
 aligned/samples.csv
 aligned/exclusions.csv
 minute/minute.csv
 five_minute/five_minute.csv
 manifest.json
                |
                v
       Downstream PM event analysis
```

The actual code is organized as separate Python modules under
`src/preprocessing/`. The diagram describes their logical
responsibilities, not necessarily every internal function call.

## 3. Files and responsibilities

### `scripts/preprocess_dataset.py`

Command-line entry point for running preprocessing against a replay or
collected dataset.

Responsibilities:

-   parse input and output paths and preprocessing options;
-   build the preprocessing configuration;
-   invoke the pipeline;
-   write the resulting dataset and manifest to the requested output
    directory.

Keep command-line defaults aligned with `PreprocessConfig`. In
particular, the rolling baseline window is configured as **20 minutes**
by default; a stale command-line value should not silently override it
with a different window.

### `src/preprocessing/__init__.py`

Package initialization for the preprocessing module. It allows the
preprocessing code to be imported as a package and can expose selected
public functions or types.

### `src/preprocessing/io.py`

Input/output and normalization helpers.

Responsibilities include reading the input dataset, converting fields
into usable types, and normalizing timestamps for downstream processing.
Timestamped samples are represented in a consistent time basis; the
pipeline uses `Asia/Kolkata` as the configured local timezone and emits
UTC-aligned timestamps in the generated time-series tables where
applicable.

Important data-handling rules:

-   Missing or unparseable timestamps remain missing; the pipeline must
    not invent wall-clock timestamps.
-   Numeric conversion failures should become missing values or explicit
    review conditions, not plausible-looking measurements.
-   Preserve the original input file. Any normalized output is a derived
    artifact.
-   Keep enough source information to trace a suspicious normalized
    record back to its raw row.

For the field-test CSV, 72 rows had no parseable timestamp. These remain
in the sample-level data and are reported separately rather than being
assigned fabricated timestamps.

### `src/preprocessing/quality.py`

Assigns quality flags and determines which measurements are eligible for
each type of analysis.

The quality system uses flags including:

-   `MISSING` --- required measurement missing;
-   `OUT_OF_RANGE` --- measurement outside configured bounds;
-   `FLATLINE` --- suspiciously unchanged readings over a long sequence;
-   `SPIKE` --- abrupt value flagged for diagnostic review;
-   `RESTART` --- device restart or boot transition;
-   `SENSOR_FAULT` --- source indicates a sensor fault;
-   `HUMIDITY` --- humidity-related reliability warning;
-   `CLOCK_UNSYNCED` --- time quality concern;
-   `STARTUP` --- startup or warm-up condition;
-   `SOURCE_REVIEW` --- source record requires review;
-   `GAP` --- missing interval or gap-related condition.

The exact set of flags attached to a row depends on the data and device
state.

#### Separate eligibility for PM and gas measurements

The pipeline distinguishes particulate-matter quality from gas-sensor
readiness:

-   `pm_quality_ok` indicates whether PM data passes the configured
    PM-specific hard checks.
-   `quality_ok` is retained as an alias for PM eligibility for
    compatibility with existing downstream code.
-   `strict_quality_ok` is a stricter PM eligibility view that also
    excludes spike-flagged samples.
-   `time_quality_ok` indicates whether the timestamp/time context is
    suitable.
-   `gas_quality_ok` reflects gas-sensor readiness based on the reported
    sensor state.
-   `quality_downgraded` indicates that quality concerns were detected.

This separation matters because a gas sensor can still be warming up or
unavailable while the PM sensor is producing usable measurements. Gas
unavailability should not automatically invalidate otherwise eligible PM
readings.

For the current field test, gas quality is false for all 5,910 rows
because the SGP41 state values indicate learning, index warm-up,
conditioning, or unavailable NOx readiness. The gas indices should
therefore not be used for source attribution in this capture.

#### Spikes are diagnostic by default

A `SPIKE` flag is not automatically a reason to discard a PM sample from
the default PM series. A rapid PM increase could be a real local plume,
but it could also be an artefact. Preserve the measurement and compare
event results with and without spike-flagged samples before drawing
conclusions.

### `src/preprocessing/aggregation.py`

Builds time-binned datasets from the sample-level data.

The pipeline creates:

-   **One-minute aggregates** in `minute/minute.csv`;
-   **Five-minute aggregates** in `five_minute/five_minute.csv`.

Aggregation is intended to make noisy sample-level telemetry easier to
inspect and analyze while retaining quality and coverage information.
The configured minimum valid fraction is 0.8 for both one-minute and
five-minute bins.

Time bins must be based on real timestamps. Untimestamped rows remain
available in the sample-level output but cannot be safely assigned to
wall-clock bins. Missing intervals should not be filled by inventing
sensor readings.

When interpreting an aggregate, check its valid-sample coverage and
quality fields. A bin containing a value is not, by itself, proof that
the full interval was observed reliably.

### `src/preprocessing/baseline.py`

Calculates a rolling PM2.5 background baseline and baseline-relative
features.

The current default configuration is:

  -------------------------------------------------------------------------------------
  Parameter                                               Default Meaning
  ---------------------------------- ---------------------------- ---------------------
  `baseline_window_min`                                        20 Rolling history
                                                                  window, in minutes

  `baseline_percentile`                                        10 Percentile used to
                                                                  estimate the
                                                                  lower/background
                                                                  PM2.5 level

  `baseline_causal`                                        `true` Use prior
                                                                  observations rather
                                                                  than future
                                                                  observations

  `baseline_min_valid_fraction`                               0.5 Minimum valid
                                                                  fraction needed for a
                                                                  baseline estimate

  `baseline_mature_valid_fraction`                            0.8 Stricter
                                                                  valid-coverage
                                                                  requirement for a
                                                                  mature baseline
  -------------------------------------------------------------------------------------

The baseline is calculated on a regular one-minute time grid. The code
does not interpolate missing PM measurements to make the history look
complete. In causal mode, the baseline uses preceding data rather than
future values, which is important if the feature will later be used for
real-time event detection.

The pipeline adds fields including:

-   `baseline_pm2_5` --- rolling PM2.5 baseline estimate;
-   `excess_pm2_5` --- measured PM2.5 minus the baseline;
-   `baseline_valid_count` --- valid observations available to the
    baseline calculation;
-   `baseline_coverage` --- observed valid coverage of the configured
    window;
-   `baseline_ready` --- baseline has enough valid history to be used
    provisionally;
-   `baseline_mature` --- baseline meets the stricter maturity
    requirements;
-   `analysis_ok` --- PM sample is eligible and the baseline is mature
    enough for baseline-relative analysis.

`baseline_ready` and `baseline_mature` are intentionally different. A
provisional baseline may be calculable before there is a full,
adequately covered history window. Downstream baseline-relative event
detection should use `analysis_ok` or otherwise explicitly enforce the
required maturity and coverage criteria.

### `src/preprocessing/pipeline.py`

Coordinates the preprocessing stages and packages the results.

The `PreprocessConfig` dataclass contains the configuration used by the
pipeline, including:

-   timezone;
-   PM minimum and maximum accepted values;
-   humidity reliability threshold;
-   flatline detection length;
-   spike detection window and threshold;
-   restart warm-up duration;
-   minimum valid fractions for minute and five-minute aggregation;
-   baseline window, percentile, causal mode, and readiness/maturity
    coverage thresholds.

The pipeline calls the quality checks, aggregation routines, and
baseline feature generation; builds the sample-level exclusions table;
and writes the output datasets and manifest.

The output `manifest.json` records configuration and run-level counts so
that results can be traced to the preprocessing settings that produced
them.

### `tests/preprocessing/`

Contains tests for preprocessing behavior. The tests should cover, at
minimum:

-   timestamp and numeric normalization;
-   missing and malformed fields;
-   PM versus gas eligibility;
-   quality flags and spike behavior;
-   minute/five-minute aggregation and valid-coverage thresholds;
-   causal baseline behavior, readiness, and maturity;
-   output counts and manifest consistency.

Run the preprocessing test suite after changing quality, aggregation,
baseline, or configuration logic. Avoid hardcoding a 20-minute baseline
in a test assertion that is intended to exercise a different configured
window; test the configured behavior instead.

## 4. Output files

A successful run writes the following artifacts under the selected
output directory.

  -----------------------------------------------------------------------
  Output                              Purpose
  ----------------------------------- -----------------------------------
  `aligned/samples.csv`               Normalized sample-level records,
                                      quality flags, PM/gas/time
                                      eligibility, and baseline-related
                                      features mapped back to samples

  `aligned/exclusions.csv`            Rows excluded from the relevant
                                      analysis paths, with exclusion
                                      reasons

  `minute/minute.csv`                 One-minute aggregates and
                                      associated
                                      quality/coverage/baseline fields

  `five_minute/five_minute.csv`       Five-minute aggregates and
                                      associated quality/coverage fields

  `manifest.json`                     Configuration, run summary, counts,
                                      and output metadata
  -----------------------------------------------------------------------

The exclusions file is not intended to replace the full sample table.
Keep `samples.csv` as the record of normalized observations, including
rows that are unsuitable for a particular analysis.

The current exclusions logic includes samples that fail PM eligibility
and samples without parseable timestamps. Diagnostic-only spike flags
are not necessarily exclusions; inspect the quality flags directly when
reviewing possible events.

## 5. Current field-test run

The latest reviewed preprocessing output has these counts:

  Metric                                  Result
  --------------------------------- ------------
  Total samples                            5,910
  Timestamped samples                      5,838
  Untimestamped samples                       72
  PM-quality-eligible samples              5,850
  PM-quality-excluded samples                 60
  One-minute bins                             99
  Five-minute bins                            21
  Baseline window                     20 minutes
  Baseline percentile                       10th
  Baseline mode                           Causal
  Baseline minimum valid fraction            0.5
  Mature-baseline valid fraction             0.8

The output timestamp range for the minute table is approximately
`2026-10-09 08:54 UTC` through `2026-10-09 10:32 UTC`, equivalent to
`14:24` through `16:02` in India Standard Time.

The original field-test CSV also contains one malformed pressure field
in the first data row. The normalized representation should set the
invalid pressure value to null, preserve the raw row for traceability,
and flag the record for review. The original CSV should remain
unchanged.

## 6. Interpretation and limitations

-   This is a single-node, single-location field capture. It describes
    conditions observed at that sensor location and time; it does not
    establish conditions across the whole campus.
-   PM event detection can be explored using the one-minute series,
    baseline-relative excess, coverage, and quality flags. Results
    should be checked against the raw sample series.
-   Do not automatically remove every spike. Review flagged spikes as
    possible sensor artefacts or genuine short-lived pollution events.
-   Do not use the current VOC/NOx indices for source attribution: the
    SGP41 states indicate that gas measurements were not ready for
    reliable interpretation.
-   Do not claim source attribution, personal exposure, health impact,
    or causal intervention effectiveness from preprocessing outputs
    alone.
-   Keep untimestamped observations in the sample-level record, but do
    not use them in time-based analyses as if their exact times were
    known.
-   Replaying the same input into the same output directory can append
    duplicate rows to the append-only raw JSONL store upstream. Use a
    fresh replay output directory for each independent validation run,
    and verify counts before preprocessing.
-   Preserve the manifest and configuration alongside any event-analysis
    output so the result is reproducible.

## 7. Recommended downstream use

1.  Verify manifest counts and ensure they match the actual CSV row
    counts.
2.  Inspect sample-level quality flags and the exclusion reasons.
3.  Plot PM2.5 and PM10 at sample and one-minute resolution, marking
    spikes, gaps, and readiness states.
4.  Identify candidate episodes from the PM series and baseline-relative
    excess, subject to baseline maturity and valid coverage.
5.  Compare candidate episodes with and without spike-flagged samples.
6.  Report event timing, observed concentrations, duration, and data
    coverage only where the timestamped observations support those
    claims.
7.  Treat source attribution and exposure estimates as separate future
    analyses requiring additional validation.

## 8. Known minor bug

The `baseline_mature` flag can turn true about one minute before a full
20 minutes have elapsed from the first timestamped minute bin. This is a
maturity-timing issue, not a corruption of the underlying PM
measurements; correct the elapsed-history check and add a regression
test before production or real-time alerting.