"""Gap-preserving 1-minute and 5-minute aggregation."""
from __future__ import annotations

import numpy as np
import pandas as pd

PM_COLUMNS = [c for c in ("pm1", "pm2_5", "pm4", "pm10")]


def minute_table(samples: pd.DataFrame, *, min_valid_fraction: float = 0.8) -> pd.DataFrame:
    """Aggregate timestamped samples to a continuous minute grid.

    Timestamp-less samples are not assigned fabricated times. They remain in the
    aligned output and are accounted for in quality/exclusions, but cannot enter
    time-based bins.
    """
    if samples.empty:
        return pd.DataFrame()
    timed = samples.loc[samples["timestamp"].notna()].copy()
    if timed.empty:
        return pd.DataFrame()
    timed["timestamp"] = pd.to_datetime(timed["timestamp"], utc=True, errors="coerce")
    timed = timed.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()
    if timed.empty:
        return pd.DataFrame()

    numeric = [c for c in PM_COLUMNS + ["temperature_c", "humidity_pct", "pressure_hpa", "voc_index", "nox_index"] if c in timed]
    # Count all packets separately from valid PM packets.
    all_counts = timed.resample("1min").size().rename("sample_count")
    quality_ok = timed.get("quality_ok", pd.Series(True, index=timed.index)).astype(bool)
    valid_counts = timed.loc[quality_ok].resample("1min").size().rename("valid_sample_count")
    medians = timed[numeric].resample("1min").median() if numeric else pd.DataFrame(index=all_counts.index)
    out = medians.join(all_counts).join(valid_counts, how="left")
    out["valid_sample_count"] = out["valid_sample_count"].fillna(0).astype(int)
    out["valid_fraction"] = out["valid_sample_count"] / out["sample_count"].replace(0, np.nan)
    out["quality_ok"] = out["valid_fraction"].fillna(0) >= min_valid_fraction
    out["quality_downgraded"] = timed.get("quality_downgraded", pd.Series(False, index=timed.index)).resample("1min").max().reindex(out.index).fillna(False).astype(bool)
    for col in ("device_id", "boot_id"):
        if col in timed:
            out[col] = timed[col].resample("1min").agg(lambda x: x.dropna().iloc[-1] if x.notna().any() else None)
    out.index.name = "timestamp"
    out = out.reset_index()
    return out


def five_minute_table(minute: pd.DataFrame, *, min_valid_fraction: float = 0.8) -> pd.DataFrame:
    """Create 5-minute summaries from minute medians; do not interpolate gaps."""
    if minute.empty:
        return pd.DataFrame()
    df = minute.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()
    numeric = [c for c in PM_COLUMNS + ["temperature_c", "humidity_pct", "pressure_hpa", "voc_index", "nox_index"] if c in df]
    valid = df.get("quality_ok", pd.Series(False, index=df.index)).astype(bool)
    valid_count = valid.resample("5min").sum().rename("valid_minute_count")
    out = df[numeric].resample("5min").median() if numeric else pd.DataFrame(index=valid_count.index)
    out = out.join(valid_count)
    out["minute_count"] = df.resample("5min").size()
    out["valid_fraction"] = out["valid_minute_count"] / 5.0
    out["quality_ok"] = out["valid_fraction"] >= min_valid_fraction
    out.index.name = "timestamp"
    return out.reset_index()