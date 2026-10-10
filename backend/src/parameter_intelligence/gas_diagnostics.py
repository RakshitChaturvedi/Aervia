"""SGP41 VOC/NOx index diagnostics; not calibrated gas concentration estimates."""

from __future__ import annotations

import pandas as pd

from .schemas import numeric

READY_STATES = {"READ_OK", "READY", "NORMAL", "VALID"}
NOT_READY_TERMS = ("LEARN", "WARM", "CONDITION", "UNAVAILABLE", "START", "INIT", "ERROR", "FAULT")


def _state_ready(value: object) -> bool:
    if pd.isna(value):
        return False
    state = str(value).strip().upper()
    if state in READY_STATES:
        return True
    if any(term in state for term in NOT_READY_TERMS):
        return False
    return False


def add_gas_diagnostics(frame: pd.DataFrame, *, rolling_window: int = 5) -> pd.DataFrame:
    out = frame.copy()
    state_column = "sgp41_state" if "sgp41_state" in out else None
    if state_column:
        ready = out[state_column].map(_state_ready).fillna(False).astype(bool)
        out["gas_sensor_ready"] = ready
        out["gas_readiness_source"] = state_column
    elif "gas_quality_ok" in out:
        ready = out["gas_quality_ok"].fillna(False).astype(bool)
        out["gas_sensor_ready"] = ready
        out["gas_readiness_source"] = "gas_quality_ok"
    else:
        ready = pd.Series(False, index=out.index)
        out["gas_sensor_ready"] = False
        out["gas_readiness_source"] = "MISSING_READINESS_FIELD"

    for column in ("voc_index", "nox_index", "sraw_voc", "sraw_nox"):
        if column not in out:
            out[f"{column}_available"] = False
            out[f"{column}_change_1m"] = float("nan")
            out[f"{column}_rolling_median_{rolling_window}m"] = float("nan")
            continue
        values = numeric(out, column)
        out[f"{column}_available"] = values.notna()
        out[f"{column}_change_1m"] = values.diff()
        out[f"{column}_rolling_median_{rolling_window}m"] = values.where(ready).rolling(
            rolling_window, min_periods=max(3, rolling_window // 2)
        ).median()

    index_present = any(c in out.columns for c in ("voc_index", "nox_index"))
    out["gas_interpretation_status"] = "READY_FOR_INDEX_ANALYSIS"
    out.loc[~ready, "gas_interpretation_status"] = "NOT_READY"
    if not index_present:
        out["gas_interpretation_status"] = "NO_GAS_INDEX_CHANNELS"
    out["gas_concentration_estimate_available"] = False
    out["gas_health_warning_eligible"] = False
    return out