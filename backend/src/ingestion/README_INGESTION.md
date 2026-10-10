# Aervia Backend — Phase 1 & 2

Local implementation of the Aervia raw ingestion layer and deterministic data replay/simulation.

## Phase 1 — Ingestion

The ingestion layer accepts four raw streams:

- `sensor` — SPS30/BME280/optional SGP41 telemetry and node health
- `activity` — observer events such as vehicles, bus idling, crowds and dust
- `weather` — external weather/wind observations
- `reference` — nearby official/reference-station observations

It validates the message shape and stores records append-only as JSONL. The ingestion layer does **not** perform cleaning, interpolation, humidity correction, aggregation, baseline estimation, event detection, regression, or ML.

### Transport

`MQTTIngestionConsumer` is intentionally thin:

```text
MQTT → validate → stream ingestor → raw store
```

No analysis is triggered from the MQTT callback. The same ingestion handlers can later sit behind AWS IoT Core/SQS.

### Local raw layout

```text
backend/data/raw/
├── sensor/sensor.jsonl
├── activity/activity.jsonl
├── weather/weather.jsonl
└── reference/reference.jsonl
```

## Phase 2 — Simulator and replay

The real sensor is not required during development. A deterministic simulator produces controlled synthetic input containing:

- ~1 Hz sensor telemetry
- minute-level weather/reference data
- sparse human activity observations
- two known pollution episodes
- deterministic noise and timestamps

Run:

```bash
python scripts/simulate_dataset.py
python scripts/inspect_dataset.py data/simulated/input
python scripts/replay.py data/simulated/input --output data/raw
```

The simulator data is explicitly **synthetic development data**, not a measurement and not a substitute for the real gate experiment.

Replay passes data through the same `MQTTIngestionConsumer` used by the real transport path. This gives preprocessing a deterministic dataset to test against before hardware is available.

## Current boundary

```text
                PHASE 1 + 2

Sensor / Activity / Weather / Reference
                  │
                  ▼
            Ingestion layer
                  │
                  ▼
             Raw JSONL
                  │
                  ▼
          Replay / test dataset
                  │
                  ▼
             PHASE 3
             preprocessing
```

Preprocessing will own clock alignment, quality flags, 1-minute/5-minute aggregation, background estimation, and excess calculation.

## Live IoT export workflow

The ingestion schemas accept the live firmware names (`timestamp_ist`, `device_id`, `sequence`, `pm2_5_ug_m3`, `temp_c`, `humidity_rh_pct`, readiness fields and quality flags) while retaining the full source row in `raw_payload`. A missing timestamp is permitted for records captured before clock synchronization; naive/non-timezone timestamps are rejected when supplied.

```bash
python scripts/inspect_dataset.py /path/to/live-export.txt
python scripts/replay.py /path/to/live-export.txt --output data/raw_live
python -m pytest -q
```

`inspect_dataset.py` and `replay.py` accept delimited CSV/TSV/TXT files as well as the JSONL stream directory format. Use a fresh output directory for each replay: persistence is append-only. Duplicate suppression is process-local; it is not a durable exactly-once guarantee across process restarts. Quality flags are preserved, not silently converted into a universal validity decision. Preprocessing must apply the analysis-specific quality policy.