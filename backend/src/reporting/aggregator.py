from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import hashlib
import json
import pandas as pd

def parse_utc(value: Any):
    if value is None or value == "":
        return None
    try:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            return None
        return ts.tz_convert("UTC")
    except Exception:
        return None

def load_json(path):
    if path is None:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def rows_from_payload(payload, preferred_keys=()):
    """Accept a list directly or find a list under common output keys."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in preferred_keys:
            if isinstance(payload.get(key), list):
                return payload[key]
        for value in payload.values():
            if isinstance(value, list) and (not value or isinstance(value[0], dict)):
                return value
    return []

def filter_window(rows, start_utc=None, end_utc=None, time_keys=("start_utc","start_time_utc","timestamp","event_start_utc")):
    start, end = parse_utc(start_utc), parse_utc(end_utc)
    if start is None and end is None:
        return rows
    filtered = []
    for row in rows:
        ts = None
        for key in time_keys:
            ts = parse_utc(row.get(key))
            if ts is not None:
                break
        if ts is None:
            # Keep un-timestamped records only when no window filter is applied.
            continue
        if (start is None or ts >= start) and (end is None or ts <= end):
            filtered.append(row)
    return filtered

def load_feature_summary(path, start_utc=None, end_utc=None):
    if not path:
        return {"status": "NOT_PROVIDED"}
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        return {"status": "FAILED_VALIDATION", "reason": "features CSV has no timestamp column"}
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    start, end = parse_utc(start_utc), parse_utc(end_utc)
    mask = ts.notna()
    if start is not None:
        mask &= ts >= start
    if end is not None:
        mask &= ts <= end
    frame = df.loc[mask].copy()
    if frame.empty:
        return {"status": "INSUFFICIENT_DATA", "rows": 0}
    def numeric_max(column):
        if column not in frame:
            return None
        vals = pd.to_numeric(frame[column], errors="coerce").dropna()
        return float(vals.max()) if len(vals) else None
    def count_true(column):
        if column not in frame:
            return None
        return int(frame[column].astype(str).str.lower().isin(["true","1","yes"]).sum())
    eligible_col = "analysis_ok" if "analysis_ok" in frame else "quality_ok"
    eligible = count_true(eligible_col)
    return {
        "status": "OK",
        "rows": int(len(frame)),
        "timestamped_rows": int(ts.loc[mask].notna().sum()),
        "window_start_utc": frame["timestamp"].iloc[0],
        "window_end_utc": frame["timestamp"].iloc[-1],
        "eligible_rows": eligible,
        "eligible_fraction": (eligible / len(frame)) if eligible is not None and len(frame) else None,
        "max_pm2_5_ug_m3": numeric_max("pm2_5"),
        "max_pm10_ug_m3": numeric_max("pm10"),
        "max_pm2_5_excess_ug_m3": numeric_max("pm2_5_excess"),
        "gas_ready_rows": count_true("gas_ready") if "gas_ready" in frame else 0,
        "humidity_high_rows": count_true("humidity_high_flag"),
    }

def stable_id(*parts):
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]