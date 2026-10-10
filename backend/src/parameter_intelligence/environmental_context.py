"""Environmental context features; no unsupported PM correction is applied."""

from __future__ import annotations

import pandas as pd

from .schemas import ENVIRONMENT_COLUMNS, numeric


def add_environmental_features(frame: pd.DataFrame, *, rolling_window: int = 5) -> pd.DataFrame:
    out = frame.copy()
    for column in ENVIRONMENT_COLUMNS:
        if column not in out:
            out[f"{column}_available"] = False
            out[f"{column}_change_1m"] = float("nan")
            out[f"{column}_rolling_mean_{rolling_window}m"] = float("nan")
            continue
        values = numeric(out, column)
        out[f"{column}_available"] = values.notna()
        out[f"{column}_change_1m"] = values.diff()
        out[f"{column}_rolling_mean_{rolling_window}m"] = values.rolling(
            rolling_window, min_periods=max(2, int(rolling_window * 0.6))
        ).mean()

    if "humidity_pct" in out:
        humidity = numeric(out, "humidity_pct")
        out["humidity_high_flag"] = humidity >= 90.0
        out["humidity_reliability_note"] = "HIGH_HUMIDITY_REVIEW" 
        out.loc[humidity.isna() | (humidity < 90.0), "humidity_reliability_note"] = "NO_HIGH_HUMIDITY_FLAG"
    else:
        out["humidity_high_flag"] = False
        out["humidity_reliability_note"] = "HUMIDITY_UNAVAILABLE"

    # This layer provides context only. It intentionally does not alter PM readings.
    out["pm_humidity_corrected"] = False
    return out