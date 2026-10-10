# Aervia Layer 5 --- Advisory Engine

## Overview

The Advisory Engine converts Layer 4 warning records into structured,
evidence-backed recommendations for operators. It combines deterministic
recommendation rules with optional Gemini-generated wording.

The rules select the approved actions. Gemini may improve the wording of
the summary and reasoning, but it must not independently change the
warning severity or invent new action IDs. If LLM generation or
validation fails, the engine falls back to deterministic output.

This is a prototype. Advisory output is operational guidance, not
medical advice.

## Position in the Aervia pipeline

``` text
Layer 3A — Parameter Intelligence
              |
Layer 3B — General Analytics
              |
Layer 4 — Warning Engine
              |
Layer 5 — Advisory Engine
  ├── Context builder
  ├── Deterministic recommendation rules
  ├── Optional Gemini wording generation
  └── Output validation and deterministic fallback
              |
Dashboard / API integration
```

Layer 5 consumes the warning records and, when provided, the Layer 3A
parameter features and Layer 3B analytics outputs. It produces one
advisory per input warning.

## Repository layout

Install the Layer 5 files into the existing `backend/` directory:

``` text
backend/
├── .env.example
├── .env                         # Create locally; do not commit
├── src/
│   └── advisory/
│       ├── __init__.py
│       ├── config.py
│       ├── schemas.py
│       ├── context_builder.py
│       ├── rules.py
│       ├── llm_generator.py
│       ├── validator.py
│       └── engine.py
├── scripts/
│   └── run_advisory_engine.py
└── tests/
    └── advisory/
        └── test_advisory_engine.py
```

The exact set of files may differ slightly by the installed package
revision.

## Configuration

Run commands from the `backend/` directory. The runner expects the
environment file at `backend/.env`.

Create it from the template:

``` bash
cp .env.example .env
```

Example `.env`:

``` dotenv
GEMINI_API_KEY=
AERVIA_ADVISORY_LLM_ENABLED=false
GEMINI_MODEL=gemini-3.8-flash
AERVIA_ADVISORY_LANGUAGE=en
AERVIA_ADVISORY_MAX_ACTIONS=4
```

Configuration fields:

  -----------------------------------------------------------------------
  Variable                            Purpose
  ----------------------------------- -----------------------------------
  `GEMINI_API_KEY`                    Gemini API key. Keep it private and
                                      never commit it.

  `AERVIA_ADVISORY_LLM_ENABLED`       Enables optional LLM wording when
                                      set to `true`.

  `GEMINI_MODEL`                      Gemini model identifier. Use a
                                      model currently available to your
                                      API key.

  `AERVIA_ADVISORY_LANGUAGE`          Requested advisory language;
                                      currently configured with `en`,
                                      with `hi` and `kn` intended for
                                      Hindi and Kannada. Check the
                                      installed version's translation
                                      coverage before relying on all
                                      fields being translated.

  `AERVIA_ADVISORY_MAX_ACTIONS`       Maximum number of approved actions
                                      to include per advisory.
  -----------------------------------------------------------------------

Add `.env` to `.gitignore`. Do not put API keys in source code, logs,
screenshots, or committed configuration files.

### Dependencies

The deterministic path does not require a Gemini API key. For optional
Gemini generation, install the packages in the active backend virtual
environment:

``` bash
python -m pip install python-dotenv google-genai
```

If the repository already defines these dependencies, install the
project's declared requirements instead.

## Run the engine

From `backend/`, run against the current Layer 4 and Layer 3 outputs:

``` bash
PYTHONPATH=. python scripts/run_advisory_engine.py \
  --warnings data/warnings/ft1_final_v2/warnings.json \
  --analytics-dir data/analytics/ft1_final_v2 \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/advisories/ft1_final_v2
```

To force deterministic output regardless of `.env` settings:

``` bash
PYTHONPATH=. python scripts/run_advisory_engine.py \
  --warnings data/warnings/ft1_final_v2/warnings.json \
  --analytics-dir data/analytics/ft1_final_v2 \
  --features data/parameter_intelligence/ft1_final_v2/features.csv \
  --output data/advisories/ft1_final_v2 \
  --disable-llm
```

The exact input paths can be changed to match the dataset being
processed.

### Expected outputs

``` text
data/advisories/ft1_final_v2/
├── advisories.json
└── advisories.csv
```

The JSON output contains the complete structured advisory records and
run metadata. The CSV is intended for convenient inspection and
downstream tabular workflows.

## Advisory workflow

1.  **Read warnings:** load the warning records produced by Layer 4.
2.  **Build context:** attach available event, recovery, exposure,
    parameter-readiness and quality information.
3.  **Select actions:** deterministic rules choose approved action IDs
    based on warning severity and event context.
4.  **Generate wording (optional):** Gemini may rewrite the summary and
    reasoning using the supplied evidence and approved action set.
5.  **Validate:** check generated output against the expected structure
    and allowed actions.
6.  **Fallback:** if generation or validation fails, produce
    deterministic wording instead.
7.  **Write outputs:** export JSON and CSV with generation mode and
    supporting evidence.

## Output fields

Each advisory can contain:

-   `advisory_id`, `warning_id`, `event_id`: identifiers linking the
    advisory to its source warning and event.
-   `status`: generation status.
-   `language`: configured language.
-   `summary`: short description of the observed event.
-   `reasoning`: explanation of the warning and relevant uncertainty.
-   `actions`: approved recommendations, including action ID, title,
    instruction, rationale, urgency, audience and evidence references.
-   `evidence`: measurements and warning fields supporting the advisory.
-   `uncertainty`: important limits on interpretation.
-   `limitations`: prototype and measurement constraints.
-   `generation_mode`: identifies whether wording came from Gemini or
    deterministic fallback.
-   `generation_note`: optional explanation when the LLM path failed.
-   `input_fingerprint`: identifier for the inputs used to generate the
    advisory.

Always inspect `generation_mode`. A successful overall run
(`status: OK`) does not necessarily mean Gemini generated every
advisory; individual records may use deterministic fallback.

## Interpreting the prototype's advice

The current rule set is designed for operator-oriented follow-up, for
example:

-   inspect the immediate monitoring area without assuming a pollution
    source;
-   verify subsequent valid sensor readings;
-   confirm current conditions when a recording ends during an event;
-   avoid inferring gas safety or gas absence when gas sensors are not
    ready.

Recommendations should remain proportional to the evidence available. A
single monitoring node does not establish campus-wide conditions. The
prototype severity categories are not official AQI categories or
medical-risk assessments. Concentration-time integrals are not personal
inhaled dose or population exposure.

## Gemini troubleshooting

Test the model independently if the engine falls back to deterministic
output. From `backend/`:

``` bash
python - <<'PY'
from dotenv import load_dotenv
from google import genai
import os

load_dotenv(".env")
key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not key:
    raise SystemExit("GEMINI_API_KEY is missing from backend/.env")

try:
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=model,
        contents="Reply with exactly: GEMINI_OK"
    )
    print("Model:", model)
    print("Response:", response.text)
except Exception as exc:
    print("Exception type:", type(exc).__name__)
    print("Exception:", str(exc))
PY
```

If the test fails, inspect the exception for authentication, model
availability, quota, request or server errors. If the test succeeds but
Layer 5 falls back, inspect the advisory generator's prompt, response
parsing and validation. Log the exception without exposing API keys or
request headers.

Gemini model availability can change. Use a model identifier currently
supported by your Google AI API configuration.

## Tests

From `backend/`:

``` bash
PYTHONPATH=. python -m unittest discover -s tests/advisory -v
```

Tests should cover deterministic recommendations, severity-dependent
actions, capture-boundary handling, unavailable gas readings, invalid
LLM responses, and deterministic fallback when generation fails.

## Current prototype limitations

-   Recommendations are selected by a small deterministic rule set.
-   LLM output validation does not guarantee that every factual phrase
    in generated prose is correct; keep evidence fields and approved
    actions authoritative.
-   Language coverage may not be complete across every output field.
-   The current dataset has gas measurements marked not ready and
    particle-distribution semantics not validated.
-   There is no proof of campus-wide representativeness or
    pollution-source attribution from one node.
-   Notifications are not delivered by this engine; it generates
    advisory records for downstream API/dashboard integration.

## Suggested next step

Integrate `advisories.json` into the dashboard/API, expose the
warning-to-advisory relationship, and show `generation_mode` in
diagnostic logs. Keep deterministic fallback available so the advisory
workflow remains usable when Gemini is unavailable.