"""Orchestrate parameter-specific feature engineering on preprocessed minute data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .environmental_context import add_environmental_features
from .gas_diagnostics import add_gas_diagnostics
from .particle_distribution import add_particle_distribution_features
from .particulate import add_particulate_features
from .schemas import COUNT_COLUMNS, ENVIRONMENT_COLUMNS, GAS_COLUMNS, PM_COLUMNS, require_timestamp


@dataclass(frozen=True)
class FeatureConfig:
    rolling_window_min: int = 5
    min_count_valid_points: int = 3
    pm_ordering_tolerance: float = 5.0
    high_humidity_pct: float = 90.0

    def __post_init__(self) -> None:
        if self.rolling_window_min < 2:
            raise ValueError("rolling_window_min must be >= 2")
        if self.min_count_valid_points < 1:
            raise ValueError("min_count_valid_points must be >= 1")
        if self.pm_ordering_tolerance < 0:
            raise ValueError("pm_ordering_tolerance must be >= 0")
        if not 0 <= self.high_humidity_pct <= 100:
            raise ValueError("high_humidity_pct must be between 0 and 100")


def _aggregate_sample_channels(samples: pd.DataFrame, minute_timestamps: pd.Series) -> pd.DataFrame:
    """Aggregate optional sample-only channels to minute bins without interpolation."""
    if "timestamp" not in samples:
        return pd.DataFrame({"timestamp": minute_timestamps})
    source = samples.copy()
    source["timestamp"] = pd.to_datetime(source["timestamp"], errors="coerce", utc=True)
    source = source.loc[source["timestamp"].notna()].copy()
    source["timestamp"] = source["timestamp"].dt.floor("min")
    cols = [c for c in (*COUNT_COLUMNS, "sraw_voc", "sraw_nox") if c in source.columns]
    if not cols:
        return pd.DataFrame({"timestamp": minute_timestamps})
    for col in cols:
        source[col] = pd.to_numeric(source[col], errors="coerce")
    grouped = source.groupby("timestamp", as_index=False)[cols].median(numeric_only=True)
    return grouped


def build_parameter_features(
    minute_data: pd.DataFrame,
    *,
    samples: pd.DataFrame | None = None,
    config: FeatureConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build deterministic features and a compact manifest.

    `minute_data` should be the output of preprocessing (`minute/minute.csv`).
    `samples` is optional and supplies channels not retained by minute aggregation,
    such as particle number concentration and SGP41 state.
    """
    cfg = config or FeatureConfig()
    minute = require_timestamp(minute_data, name="minute_data")
    if samples is not None:
        optional = _aggregate_sample_channels(samples, minute["timestamp"])
        state_cols = [c for c in ("timestamp", "sgp41_state", "sps30_state") if c in samples.columns]
        if "sgp41_state" in state_cols:
            state_src = samples[state_cols].copy()
            state_src["timestamp"] = pd.to_datetime(state_src["timestamp"], errors="coerce", utc=True)
            state_src = state_src.loc[state_src["timestamp"].notna()].copy()
            state_src["timestamp"] = state_src["timestamp"].dt.floor("min")
            state_src = state_src.groupby("timestamp", as_index=False).last()
            optional = optional.merge(state_src[["timestamp", "sgp41_state"]], on="timestamp", how="left")
        minute = minute.merge(optional, on="timestamp", how="left", suffixes=("", "_sample"))

    minute = minute.sort_values("timestamp").reset_index(drop=True)
    minute = add_particulate_features(
        minute, rolling_window=cfg.rolling_window_min, ordering_tolerance=cfg.pm_ordering_tolerance
    )
    minute = add_particle_distribution_features(
        minute, rolling_window=cfg.rolling_window_min, min_valid_points=cfg.min_count_valid_points
    )
    minute = add_gas_diagnostics(minute, rolling_window=cfg.rolling_window_min)
    minute = add_environmental_features(minute, rolling_window=cfg.rolling_window_min)

    # Apply config rather than a hardcoded environmental threshold.
    if "humidity_pct" in minute:
        humidity = pd.to_numeric(minute["humidity_pct"], errors="coerce")
        minute["humidity_high_flag"] = humidity >= cfg.high_humidity_pct
        minute["humidity_reliability_note"] = "NO_HIGH_HUMIDITY_FLAG"
        minute.loc[humidity.isna(), "humidity_reliability_note"] = "HUMIDITY_UNAVAILABLE"
        minute.loc[humidity >= cfg.high_humidity_pct, "humidity_reliability_note"] = "HIGH_HUMIDITY_REVIEW"

    minute["parameter_features_version"] = "0.1.0"
    minute["parameter_feature_status"] = "PARTIAL"
    required_pm = [c for c in ("pm2_5",) if c in minute]
    if required_pm and pd.to_numeric(minute[required_pm[0]], errors="coerce").notna().any():
        minute["parameter_feature_status"] = "OK"
    if not required_pm:
        minute["parameter_feature_status"] = "INSUFFICIENT_DATA"

    def present_count(columns: tuple[str, ...]) -> int:
        return sum(c in minute.columns and pd.to_numeric(minute[c], errors="coerce").notna().any() for c in columns)

    manifest = {
        "feature_version": "0.1.0",
        "config": asdict(cfg),
        "input_minute_rows": int(len(minute)),
        "output_rows": int(len(minute)),
        "timestamp_min": minute["timestamp"].min().isoformat() if len(minute) else None,
        "timestamp_max": minute["timestamp"].max().isoformat() if len(minute) else None,
        "available_pm_channels": [c for c in PM_COLUMNS if c in minute and pd.to_numeric(minute[c], errors="coerce").notna().any()],
        "available_particle_count_channels": [c for c in COUNT_COLUMNS if c in minute and pd.to_numeric(minute[c], errors="coerce").notna().any()],
        "available_environment_channels": [c for c in ENVIRONMENT_COLUMNS if c in minute and pd.to_numeric(minute[c], errors="coerce").notna().any()],
        "available_gas_channels": [c for c in GAS_COLUMNS if c in minute and pd.to_numeric(minute[c], errors="coerce").notna().any()],
        "gas_ready_rows": int(minute["gas_sensor_ready"].sum()) if "gas_sensor_ready" in minute else 0,
        "gas_concentration_estimates_enabled": False,
        "particle_count_semantics_verified": False,
        "pm_humidity_correction_applied": False,
        "notes": [
            "Particle count channel semantics must be confirmed before size-bin arithmetic.",
            "VOC/NOx indices are not calibrated gas concentrations.",
            "Environmental context does not correct or overwrite PM measurements.",
        ],
    }
    return minute, manifest