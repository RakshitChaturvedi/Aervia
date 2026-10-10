"""Quality-aware particulate concentration features.

PM size channels are cumulative cut-point fractions. Differences are exposed as
candidate size-band estimates only when the observed ordering is plausible; they
are not treated as independent sensor measurements.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .schemas import PM_COLUMNS, numeric


def add_particulate_features(
    frame: pd.DataFrame,
    *,
    baseline_column: str = "baseline_pm2_5",
    rolling_window: int = 5,
    ordering_tolerance: float = 5.0,
) -> pd.DataFrame:
    """Add trend, excess, and cautiously validated size-band features to a copy."""
    out = frame.copy()
    for column in PM_COLUMNS:
        if column not in out:
            out[f"{column}_available"] = False
            continue
        values = numeric(out, column)
        out[f"{column}_available"] = values.notna()
        out[f"{column}_change_1m"] = values.diff()
        out[f"{column}_rolling_mean_{rolling_window}m"] = values.rolling(
            rolling_window, min_periods=max(2, int(np.ceil(rolling_window * 0.6)) )
        ).mean()
        out[f"{column}_rate_per_min"] = values.diff()

    pm25 = numeric(out, "pm2_5")
    if baseline_column in out:
        baseline = numeric(out, baseline_column)
        out["pm2_5_excess"] = pm25 - baseline
        out["pm2_5_positive_excess"] = (pm25 - baseline).clip(lower=0)
        out["pm2_5_baseline_available"] = baseline.notna()
    else:
        out["pm2_5_excess"] = np.nan
        out["pm2_5_positive_excess"] = np.nan
        out["pm2_5_baseline_available"] = False

    # Difference of cumulative PM fractions. Preserve negative/raw differences for QA;
    # only publish a candidate band when the ordering is plausible within tolerance.
    band_specs = (
        ("pm1", "pm2_5", "pm1_to_pm2_5_band"),
        ("pm2_5", "pm4", "pm2_5_to_pm4_band"),
        ("pm4", "pm10", "pm4_to_pm10_band"),
    )
    for lower_col, upper_col, name in band_specs:
        if lower_col in out and upper_col in out:
            lower = numeric(out, lower_col)
            upper = numeric(out, upper_col)
            diff = upper - lower
            plausible = lower.notna() & upper.notna() & (diff >= -ordering_tolerance)
            out[f"{name}_raw"] = diff
            out[name] = diff.where(plausible).clip(lower=0)
            out[f"{name}_valid"] = plausible
        else:
            out[f"{name}_raw"] = np.nan
            out[name] = np.nan
            out[f"{name}_valid"] = False

    # A negative difference beyond tolerance is a consistency flag, not a corrected value.
    available_pm = [c for c in PM_COLUMNS if c in out]
    if len(available_pm) >= 2:
        values = pd.DataFrame({c: numeric(out, c) for c in available_pm}, index=out.index)
        ordered = values.apply(lambda row: all(row[a] <= row[b] + ordering_tolerance
                                               for a, b in zip(available_pm, available_pm[1:])
                                               if pd.notna(row[a]) and pd.notna(row[b])), axis=1)
        out["pm_fraction_ordering_ok"] = ordered
    else:
        out["pm_fraction_ordering_ok"] = False
    return out