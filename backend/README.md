
# Aervia — Final Pipeline

```text
1. Data Ingestion
        ↓
2. Data Preprocessing
        ↓
3. Event Detection
        ↓
4. Recovery Profile
        ↓
5. Exposure Burden
        ↓
6. Activity Association
        ↓
7. Intervention Check
        ↓
8. Orchestration + Report Generation
        ↓
9. UI
```

The important thing is that **3–7 are separate analytical modules**, not one giant ML pipeline.

---

# 1. Data Ingestion

### Purpose

Get all raw inputs into a consistent local representation.

### Inputs

#### Sensor

```text
PM1
PM2.5
PM4
PM10
particle counts
VOC index
NOx index
temperature
humidity
pressure
timestamp
device health
battery
RSSI
```

Only fields actually supplied by the hardware are recorded. The competition document explicitly says not to pretend the sensor provides fields it doesn't provide. aervia plan

#### Activity log

```text
vehicle count
vehicle class
bus arrival
bus departure
bus idling
pedestrian/crowd level
dust
sweeping
construction
other observations
```

#### External data

```text
weather
wind
reference PM
NO2 if an actual source exists
```

### Repository

```text
backend/src/ingestion/

├── sensor.py
├── activity.py
├── weather.py
├── reference.py
├── schemas.py
└── loaders.py
```

### Output

A set of raw, timestamped datasets.

```text
raw/
├── sensor/
├── activity/
├── weather/
└── reference/
```

**Important:** ingestion does not perform analysis.

---

# 2. Data Preprocessing

### Purpose

Turn the independent raw streams into an aligned, quality-controlled dataset.

```text
Sensor
Activity
Weather
Reference PM
      ↓
Time Alignment
      ↓
Quality Control
      ↓
Aggregation
      ↓
Processed Dataset
```

### Components

```text
backend/src/preprocessing/

├── alignment.py
├── quality.py
├── aggregation.py
├── baseline.py
└── pipeline.py
```

### Alignment

Everything needs to share a common timeline.

```text
timestamp
device timestamp correction
timezone
missing intervals
```

The plan explicitly requires sensor, activity, weather, and reference data to share timestamps, with any clock correction recorded rather than hidden. aervia plan

### Quality control

Detect:

- missing packets
- impossible values
- flatline
- one-sample spikes
- restarts
- sensor faults
- problematic humidity conditions

Don't delete bad observations.

```text
value
+
quality_flag
```

### Aggregation

Keep:

```text
~1-second raw
      ↓
1-minute median
      ↓
5-minute summary
```

The 1-minute median is specifically called for in the plan. aervia plan

### Baseline/excess

Also produce:

```text
B(t) = background
X(t) = max(C(t) - B(t), 0)
```

The baseline methodology should be configurable so we can test different rolling windows/percentiles. aervia plan

### Output

A canonical processed dataset:

```text
processed/
├── minute/
├── five_minute/
└── aligned/
```

---

# 3. Analysis — Event Detection

This is the first of the five analyses.

### Purpose

Answer:

> **What pollution episodes actually occurred?**

Input:

```text
5-minute PM
+
baseline
+
excess
+
quality
```

### Detection rule

An event requires:

```text
excess > predefined threshold
AND
persists for minimum duration
AND
rise is genuine
AND
quality is acceptable
```

The threshold must be decided **before** looking at the result we want to demonstrate. aervia plan

### Output

Each event becomes a structured object:

```text
Event
├── event_id
├── start_time
├── end_time
├── duration
├── peak_pm25
├── peak_excess
├── integrated_excess
├── rise_rate
├── fall_rate
├── quality
├── confidence
└── observations
```

### Repository

```text
backend/src/analyses/event_detection/

├── detector.py
├── thresholds.py
├── metrics.py
└── models.py
```

---

# 4. Analysis — Recovery Profile

### Purpose

Answer:

> **After a pollution peak, how quickly did the excess decline?**

For each suitable event:

```text
C(t) - B = A e^(-λt)
```

Calculate:

```text
λ
half-life = ln(2) / λ
t90 = ln(10) / λ
```

Also calculate fit quality.

### Critical output

Not every event will fit.

Therefore:

```text
recovery_status =
    FIT
    POOR_FIT
    DOES_NOT_FIT
    INSUFFICIENT_DATA
```

The document specifically says not to force the curve and to describe the result as an **observed outdoor-gate recovery time**, not a room ventilation rate. aervia plan

### Repository

```text
backend/src/analyses/recovery/

├── fitter.py
├── metrics.py
└── models.py
```

---

# 5. Analysis — Exposure Burden

### Purpose

Answer:

> **How much excess pollution accumulated during each event/period?**

Primary metric:

```text
I = Σ X(t) × Δt
```

Units:

```text
µg/m³ · hour
```

For periods:

```text
morning
midday
evening
```

### Optional population weighting

Only when actual people counts exist:

```text
E = Σ X(t) × N(t) × Δt
```

This is a **burden proxy**, not inhaled dose or medical risk. If people aren't actually counted, don't calculate it. aervia plan

### Repository

```text
backend/src/analyses/exposure/

├── burden.py
├── population.py
└── models.py
```

---

# 6. Analysis — Activity Association

### Purpose

Answer:

> **What activities were happening around pollution events, and what patterns are associated with excess PM?**

Start with descriptive analysis:

```text
Traffic level
      vs
Excess PM
```

```text
Bus idling
      vs
Event occurrence
```

```text
Wind
      vs
Excess PM
```

```text
Time of day
      vs
Event frequency
```

Only if enough clean observations exist, perform regression:

```text
ln(X + ε)
    ~
traffic
+ wind
+ humidity
+ time of day
```

The output should contain:

```text
coefficient
uncertainty
sample size
effect size
model diagnostics
```

And the language must remain:

> "associated with"

rather than:

> "caused by"

The source explicitly requires this distinction. aervia plan

### Repository

```text
backend/src/analyses/activity/

├── features.py
├── comparisons.py
├── regression.py
└── models.py
```

---

# 7. Analysis — Intervention Check

This is the fifth analysis.

### Purpose

Answer:

> **Did the practical intervention correspond with a measurable difference afterward?**

Example:

```text
Intervention:
Engines off while buses wait
```

Record:

```text
intervention
start
end
location
responsible role
```

Then identify comparable periods.

```text
BEFORE
average excess
event count
weather
traffic

        vs

AFTER
average excess
event count
weather
traffic
```

Calculate:

```text
difference =
average excess before
-
average excess after
```

and:

```text
percent =
difference / average excess before × 100
```

But if conditions aren't comparable:

```text
status = INCONCLUSIVE
```

rather than claiming the intervention worked. aervia plan

### Repository

```text
backend/src/analyses/intervention/

├── matcher.py
├── comparison.py
├── verification.py
└── models.py
```

---

# 8. Orchestration + Report Generation

This is where we bring everything together.

But importantly, **this is not a giant function called for every IoT packet.**

It operates at the dataset/window/experiment level.

## Orchestrator

```text
backend/src/orchestration/

├── pipeline.py
├── stages.py
└── state.py
```

Conceptually:

```python
run_experiment()
```

does:

```text
Raw data
   ↓
Ingestion validation
   ↓
Preprocessing
   ↓
Event Detection
   ↓
Recovery
   ↓
Exposure
   ↓
Activity Association
   ↓
Intervention Check
   ↓
Results
```

Each stage is independently callable.

For example:

```python
events = detect_events(processed_data)

recovery = analyze_recovery(
    processed_data,
    events
)

exposure = calculate_exposure(
    processed_data,
    events
)

activity = analyze_activity(
    processed_data,
    events
)

intervention = evaluate_intervention(
    processed_data,
    events
)
```

This makes testing much easier.

---

## Report generation

```text
backend/src/reports/

├── college_gate.py
├── sections/
│   ├── timeline.py
│   ├── recovery.py
│   ├── exposure.py
│   ├── activity.py
│   └── intervention.py
└── renderer.py
```

The final report contains:

### 1. Timeline

- PM trace
- event markers
- peak
- duration
- integrated excess
- observations
- confidence

### 2. Recovery

- recovery curves
- half-life
- t90
- good/poor fits

### 3. Exposure ledger

- event-level integrated excess
- morning/midday/evening totals
- people-weighted burden if available
- unattributed periods

### 4. Activity

- traffic
- idling
- weather
- time-of-day
- regression if justified

### 5. Action

- recommended intervention
- before/after
- uncertainty
- continue/change/drop recommendation

These correspond directly to the report structure in the plan. aervia plan

---

# 9. UI Specification

This isn't your implementation responsibility, but we should give the UI developer a sufficiently precise contract.

The UI should be organized around **Track → Warn → Change**, rather than looking like a generic city AQ dashboard. The competition document explicitly says the gate experiment should be the story, with the city dashboard remaining secondary context. aervia plan

## A. Overview / Gate Dashboard

First screen.

Show:

```text
College Gate
────────────────────────────

Current PM2.5
Current status

Today's events
Peak event
Total integrated excess

Active alert

Current activity
Weather
```

Also:

```text
PM2.5 timeline
────────────────────────────
        /\       /\
_______/  \_____/  \____
        ↑       ↑
      Event   Event
```

The user should immediately understand **what is happening at the gate**.

---

# B. Event Timeline

A chronological view:

```text
08:10 ─────────────────────
08:25       EVENT #1
08:40 ─────────────────────
09:15              EVENT #2
09:40 ─────────────────────
```

Clicking an event opens its detail page.

---

# C. Event Detail

This should be the most important UI screen.

```text
EVENT #12
────────────────────────────

Severity        HIGH
Confidence      MEDIUM
Duration        14 min

Peak PM2.5      71 µg/m³
Peak Excess     48 µg/m³
Integrated      7.2 µg/m³·h
```

Then:

### Timeline

PM2.5 + baseline + excess.

### Recovery

Show:

```text
Observed decline
Fitted curve
Half-life
t90
Fit quality
```

### Context

```text
Traffic       HIGH
Bus idling    YES
Wind          LOW
Humidity      71%
```

### Activity notes

```text
2 buses arrived
1 bus idling
High vehicle queue
```

### Interpretation

Clearly separate:

```text
MEASURED
CALCULATED
ASSOCIATED
HYPOTHESIS
```

This prevents the UI from turning an association into a causal claim.

---

# D. Exposure

Show an event/period ledger:

| Period | Integrated Excess | Events |
|---|---:|---:|
| Morning | ... | ... |
| Midday | ... | ... |
| Evening | ... | ... |

If population counts exist:

```text
People-weighted burden
```

Otherwise don't display a fake exposure estimate.

---

# E. Activity

Visual comparison:

```text
Traffic
████████████

PM2.5
     ╱╲
____╱  ╲____

Bus idling
        ████
```

Useful charts:

- traffic vs PM
- bus idling vs events
- wind vs PM
- time-of-day distribution

If regression is available:

```text
Traffic association
Coefficient
Uncertainty
N
```

Again, label this **association**, not source causality.

---

# F. Alerts / Warn

Small operational alert panel:

```text
⚠ ELEVATED POLLUTION EVENT

PM2.5 has remained elevated
for 12 minutes.

Confidence: Medium

Suggested check:
• Check idling buses
• Check vehicle queue

Responsible role:
Transport / Security
```

The alert should go to the person who can act, not students generally. aervia plan

---

# G. Interventions / Change

Show:

```text
INTERVENTION #04

Recommended:
Engines off while buses wait

Status:
IMPLEMENTED

Started:
08:42

Follow-up:
09:00–09:20
```

Then:

```text
Before             After

Average excess     Average excess
Event count        Event count
Traffic            Traffic
Wind               Wind
```

Finally:

```text
VERIFICATION

Observed difference: -X%
Confidence: Limited

Conclusion:
INCONCLUSIVE
```

if conditions aren't sufficiently comparable.

---

# H. Reports

Allow:

```text
Generate College-Gate Report
```

and display/download:

```text
Timeline
Recovery
Exposure
Activity
Action
Verification
```

The report should make the distinction between **measured fact, calculated estimate, and hypothesis** visually obvious. aervia plan

---

# Final Backend Structure

So I'd now lock your actual backend as:

```text
backend/
│
├── src/
│   │
│   ├── ingestion/
│   ├── preprocessing/
│   │
│   ├── analyses/
│   │   ├── event_detection/
│   │   ├── recovery/
│   │   ├── exposure/
│   │   ├── activity/
│   │   └── intervention/
│   │
│   ├── orchestration/
│   ├── reports/
│   ├── api/
│   └── config/
│
├── tests/
├── scripts/
└── README.md
```

And the **five analysis modules are deliberately independent**:

```text
                    Processed Data
                         │
            ┌────────────┼────────────┐
            │            │            │
            ▼            ▼            ▼
         Events       Exposure     Activity
            │
            ▼
        Recovery
            │
            └──────────────┐
                           ▼
                     Intervention
                           │
                           ▼
                       Results
```

That is the architecture I would use going forward. It keeps each part independently testable and maps almost one-to-one to the competition plan rather than building unnecessary infrastructure around it.