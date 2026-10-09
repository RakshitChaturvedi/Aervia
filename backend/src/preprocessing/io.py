"""Input/output helpers for ingestion replay JSONL and CSV/JSONL sensor data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ALIASES = {
    "pm2_5_ug_m3": "pm2_5",
    "pm25": "pm2_5",
    "pm2_5": "pm2_5",
    "pm10_ug_m3": "pm10",
    "pm10": "pm10",
    "pm1_ug_m3": "pm1",
    "pm1": "pm1",
    "pm4_ug_m3": "pm4",
    "pm4": "pm4",
    "temp_c": "temperature_c",
    "temperature_c": "temperature_c",
    "humidity_rh_pct": "humidity_pct",
    "humidity_rh": "humidity_pct",
    "humidity_pct": "humidity_pct",
    "pressure_hpa": "pressure_hpa",
    "voc_index": "voc_index",
    "nox_index": "nox_index",
    "timestamp_ist": "timestamp",
    "timestamp": "timestamp",
    "sequence": "sequence",
    "uptime_s": "uptime_s",
    "boot_id": "boot_id",
    "device_id": "device_id",
    "source_id": "source_id",
    "quality_flag": "source_quality_flag",
    "quality_flags": "source_quality_flags",
    "sps30_state": "sps30_state",
    "sgp41_state": "sgp41_state",
    "clock_source": "clock_source",
}

NUMERIC_COLUMNS = [
    "pm1", "pm2_5", "pm4", "pm10", "temperature_c",
    "humidity_pct", "pressure_hpa", "voc_index", "nox_index",
    "sequence", "uptime_s",
]


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten replay envelopes while retaining source metadata and raw payload."""
    payload = record.get("raw_payload")
    merged: dict[str, Any] = {}
    if isinstance(payload, dict):
        merged.update(payload)
    merged.update(record)  # canonical fields on the envelope take precedence
    out: dict[str, Any] = {}
    for key, value in merged.items():
        canonical = ALIASES.get(key, key)
        if canonical not in out or value is not None:
            out[canonical] = value
    # A null envelope timestamp must not overwrite a usable original timestamp.
    if record.get("timestamp") is None and isinstance(payload, dict):
        original = payload.get("timestamp_ist") or payload.get("timestamp")
        if original:
            out["timestamp"] = original
    out["_raw_payload"] = payload if isinstance(payload, dict) else record.get("_raw_payload")
    out["_envelope_timestamp"] = record.get("timestamp")
    out["_stream"] = record.get("stream")
    return out


def load_records(path: str | Path) -> pd.DataFrame:
    """Load CSV, JSONL, or replay output directory (sensor.jsonl).

    Untimestamped rows remain in the output. Their relative order is represented by
    input order/sequence/uptime; this function never invents wall-clock timestamps.
    """
    p = Path(path)
    if p.is_dir():
        candidate = p / "sensor.jsonl"
        if not candidate.exists():
            raise FileNotFoundError(f"No sensor.jsonl found in replay directory: {p}")
        p = candidate
    suffix = p.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        rows = []
        with p.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on line {line_number} of {p}: {exc}") from exc
                rows.append(_flatten_record(record) if isinstance(record, dict) else {})
        frame = pd.DataFrame(rows)
    elif suffix == ".csv":
        frame = pd.read_csv(p)
        frame = frame.rename(columns={k: v for k, v in ALIASES.items() if k in frame.columns})
        # Preserve the original input fields in the raw CSV; normalized columns are derived.
        frame["_raw_payload"] = None
        frame["_envelope_timestamp"] = None
        frame["_stream"] = "csv"
    else:
        raise ValueError(f"Unsupported input format: {p.suffix}; use CSV or JSONL")
    if frame.empty:
        return frame
    if "timestamp" not in frame:
        frame["timestamp"] = pd.NaT
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    for column in NUMERIC_COLUMNS:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "sequence" not in frame:
        frame["sequence"] = pd.NA
    frame["_input_order"] = range(len(frame))
    return frame


def write_table(frame: pd.DataFrame, path: str | Path) -> None:
    """Write CSV with stable timestamp formatting and without mutating input."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    output = frame.copy()
    for col in output.columns:
        if pd.api.types.is_datetime64_any_dtype(output[col]):
            output[col] = output[col].map(lambda x: x.isoformat() if pd.notna(x) else "")
    output.to_csv(p, index=False)