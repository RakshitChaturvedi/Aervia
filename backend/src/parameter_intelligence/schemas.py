"""Shared names and small validation helpers for parameter intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

TIMESTAMP_COLUMN = "timestamp"
PM_COLUMNS = ("pm1", "pm2_5", "pm4", "pm10")
COUNT_COLUMNS = (
    "nc0_5_per_cm3",
    "nc1_0_per_cm3",
    "nc2_5_per_cm3",
    "nc4_per_cm3",
    "nc10_per_cm3",
)
ENVIRONMENT_COLUMNS = ("temperature_c", "humidity_pct", "pressure_hpa")
GAS_COLUMNS = ("voc_index", "nox_index")


@dataclass(frozen=True)
class FeatureStatus:
    status: str
    reason: str | None = None


def require_timestamp(frame: pd.DataFrame, *, name: str = "dataframe") -> pd.DataFrame:
    """Return a copy with parseable timestamps; reject frames with no timestamp column."""
    if TIMESTAMP_COLUMN not in frame.columns:
        raise ValueError(f"{name} must contain a '{TIMESTAMP_COLUMN}' column")
    out = frame.copy()
    out[TIMESTAMP_COLUMN] = pd.to_datetime(out[TIMESTAMP_COLUMN], errors="coerce", utc=True)
    out = out.loc[out[TIMESTAMP_COLUMN].notna()].sort_values(TIMESTAMP_COLUMN)
    if out[TIMESTAMP_COLUMN].duplicated().any():
        raise ValueError(f"{name} must have at most one row per timestamp; aggregate duplicates first")
    return out.reset_index(drop=True)


def numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(float("nan"), index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def status_for_column(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    present = column in frame.columns
    valid = int(numeric(frame, column).notna().sum()) if present else 0
    return {
        "column": column,
        "available": present,
        "valid_count": valid,
        "status": "OK" if valid else ("UNAVAILABLE" if not present else "NO_VALID_VALUES"),
    }