from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pandas as pd


def load_json(path: Path, optional: bool = False) -> dict[str, Any] | None:
    if not path.exists():
        if optional:
            return None
        raise FileNotFoundError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def _records(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not data:
        return []
    for key in ("events", "results", "records", "profiles", "integrals"):
        value = data.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    return []


def build_context(warning: dict[str, Any], analytics_dir: Path | None, features_path: Path | None) -> dict[str, Any]:
    context: dict[str, Any] = {"warning": warning, "event": None, "recovery": None, "exposure": None, "parameter_context": {}}
    event_id = warning.get("event_id")
    if analytics_dir:
        for filename, key in (("event_detection.json", "event"), ("recovery_profile.json", "recovery"), ("exposure_burden.json", "exposure")):
            payload = load_json(analytics_dir / filename, optional=True)
            for item in _records(payload):
                candidate = item.get("event_id") or item.get("id")
                if candidate == event_id:
                    context[key] = item
                    break
    if features_path and features_path.exists():
        # Only a compact set of parameter-quality/readiness fields is exposed to the advisory generator.
        frame = pd.read_csv(features_path)
        ts_col = next((c for c in ("timestamp", "timestamp_utc", "time_utc") if c in frame.columns), None)
        if ts_col:
            frame[ts_col] = pd.to_datetime(frame[ts_col], errors="coerce", utc=True)
            peak = pd.to_datetime(warning.get("peak_utc"), errors="coerce", utc=True)
            if pd.notna(peak):
                candidates = frame.loc[frame[ts_col].eq(peak)]
                if candidates.empty:
                    candidates = frame.loc[frame[ts_col].le(peak)].tail(1)
                if not candidates.empty:
                    row = candidates.iloc[-1]
                    for col in ("parameter_feature_status", "sgp41_state", "gas_interpretation_status", "gas_ready", "gas_health_warning_eligible", "particle_distribution_status", "particle_distribution_interpretable", "quality_ok", "quality_downgraded", "humidity_pct", "temperature_c"):
                        if col in frame.columns and pd.notna(row.get(col)):
                            val = row[col]
                            context["parameter_context"][col] = val.item() if hasattr(val, "item") else val
    return context