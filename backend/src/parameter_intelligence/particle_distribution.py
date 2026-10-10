"""Particle number-concentration trend features.

The module deliberately does not derive size-bin counts from NC channels until
firmware documentation confirms whether those channels are cumulative or differential.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .schemas import COUNT_COLUMNS, numeric


def add_particle_distribution_features(
    frame: pd.DataFrame,
    *,
    rolling_window: int = 5,
    min_valid_points: int = 3,
) -> pd.DataFrame:
    out = frame.copy()
    present = [c for c in COUNT_COLUMNS if c in out.columns]
    for column in COUNT_COLUMNS:
        if column not in out:
            out[f"{column}_available"] = False
            continue
        values = numeric(out, column)
        valid = values.notna() & (values >= 0)
        out[f"{column}_available"] = valid
        out[f"{column}_change_1m"] = values.diff()
        out[f"{column}_rolling_median_{rolling_window}m"] = values.where(valid).rolling(
            rolling_window, min_periods=min_valid_points
        ).median()
        rolling = out[f"{column}_rolling_median_{rolling_window}m"]
        out[f"{column}_relative_to_rolling_median"] = values.div(rolling.where(rolling > 0))
        out[f"{column}_invalid_value"] = values.notna() & (values < 0)

    out["particle_count_channels_available"] = bool(present)
    out["particle_count_channels_present"] = len(present)

    # Channel ordering is intentionally not validated here: NC channel semantics must
    # be confirmed against the exact sensor/firmware specification first.
    out["particle_distribution_interpretable"] = False
    out["particle_distribution_status"] = (
        "CHANNELS_PRESENT_SEMANTICS_UNVERIFIED" if present else "NO_COUNT_CHANNELS"
    )
    return out