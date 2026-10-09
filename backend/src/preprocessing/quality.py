
"""Quality flags and eligibility for PM, gas, and time-dependent analysis.

Observations are retained. Spike detection is diagnostic by default:
spike-flagged PM values remain eligible for exploratory event detection.
"""

from __future__ import annotations

import json
from enum import IntFlag
from typing import Any

import numpy as np
import pandas as pd


class QualityFlag(IntFlag):
    OK = 0
    MISSING = 1
    OUT_OF_RANGE = 2
    FLATLINE = 4
    SPIKE = 8
    RESTART = 16
    SENSOR_FAULT = 32
    HUMIDITY = 64
    CLOCK_UNSYNCED = 128
    STARTUP = 256
    SOURCE_REVIEW = 512
    GAP = 1024


FLAG_LABELS = {
    flag.value: flag.name.lower()
    for flag in QualityFlag
    if flag != QualityFlag.OK
}


def _bool_source_flags(value: Any) -> set[str]:
    """Normalize serialized or native source quality flags."""
    if isinstance(value, dict):
        return {
            str(key).strip().lower()
            for key, enabled in value.items()
            if bool(enabled)
        }

    if isinstance(value, (list, tuple, set)):
        return {str(item).strip().lower() for item in value if item}

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return set()

        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Support a simple comma-separated representation.
            return {
                part.strip().lower()
                for part in value.split(",")
                if part.strip()
            }

        if isinstance(parsed, (dict, list, tuple, set)):
            return _bool_source_flags(parsed)

        return {str(parsed).strip().lower()} if parsed else set()

    return set()


def _has_token(names: set[str], tokens: tuple[str, ...]) -> bool:
    """Match complete flag names or underscore-delimited flag components."""
    for name in names:
        parts = name.replace("-", "_").split("_")
        for token in tokens:
            token_parts = token.replace("-", "_").split("_")
            if token_parts == parts:
                return True
            if token in name:
                return True
    return False


def flag_samples(
    frame: pd.DataFrame,
    *,
    pm_range: tuple[float, float] = (0.0, 1000.0),
    humidity_unreliable_pct: float = 90.0,
    flatline_samples: int = 120,
    spike_window_samples: int = 15,
    spike_n_sigma: float = 5.0,
    restart_warmup_s: float = 60.0,
) -> pd.DataFrame:
    """Add diagnostic flags and separate eligibility fields.

    Main output fields:
        quality_flags_int
        quality_flags
        quality_ok          Alias for pm_quality_ok for existing callers.
        pm_quality_ok       Suitable for PM analysis.
        strict_quality_ok   PM eligibility excluding spike-flagged samples.
        time_quality_ok     Suitable for wall-clock-dependent analysis.
        gas_quality_ok      Suitable for gas-index analysis.
        quality_downgraded  Humidity-related confidence downgrade.

    Source metadata issues do not automatically invalidate PM measurements.
    Gas readiness does not determine PM readiness.
    Spike flags are diagnostic and do not invalidate the default PM series.
    """
    if pm_range[0] >= pm_range[1]:
        raise ValueError("pm_range minimum must be less than maximum")
    if not 0 <= humidity_unreliable_pct <= 100:
        raise ValueError("humidity_unreliable_pct must be in [0, 100]")
    if spike_n_sigma <= 0:
        raise ValueError("spike_n_sigma must be positive")

    df = frame.copy().reset_index(drop=True)
    n = len(df)

    flags = np.zeros(n, dtype=np.int64)
    source_names: list[set[str]] = []

    def mark(mask: Any, flag: QualityFlag) -> None:
        values = np.asarray(
            pd.Series(mask, index=df.index).fillna(False),
            dtype=bool,
        )
        flags[values] |= int(flag)

    def numeric_column(name: str) -> pd.Series:
        return pd.to_numeric(
            df.get(name, pd.Series(np.nan, index=df.index)),
            errors="coerce",
        )

    pm = numeric_column("pm2_5")
    mark(pm.isna(), QualityFlag.MISSING)
    mark(~pm.between(pm_range[0], pm_range[1]), QualityFlag.OUT_OF_RANGE)

    humidity = numeric_column("humidity_pct")
    mark(
        humidity.notna() & humidity.ge(humidity_unreliable_pct),
        QualityFlag.HUMIDITY,
    )

    source_quality = (
        df.get("source_quality_flag", pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    source_flags = df.get(
        "source_quality_flags",
        pd.Series([None] * n, index=df.index),
    )

    for value in source_flags:
        source_names.append(_bool_source_flags(value))

    # Also handle known state columns directly. PM and gas states are separate.
    pm_state = (
        df.get("sps30_state", pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )
    gas_state = (
        df.get("sgp41_state", pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    pm_not_ready_states = {
        "SETTLING",
        "NOT_READY",
        "WARMUP",
        "WARMING",
        "CONDITIONING",
    }
    gas_ready_states = {"READ_OK", "READY"}

    pm_startup = pm_state.isin(pm_not_ready_states)
    mark(pm_startup, QualityFlag.STARTUP)

    # A source flag can refer to a specific sensor. Do not interpret gas-only
    # readiness flags as PM startup failures.
    source_pm_missing = np.zeros(n, dtype=bool)
    source_pm_startup = np.zeros(n, dtype=bool)
    source_sensor_fault = np.zeros(n, dtype=bool)
    source_clock_unsynced = np.zeros(n, dtype=bool)
    source_spike = np.zeros(n, dtype=bool)

    for i, names in enumerate(source_names):
        normalized = {name.replace("-", "_").lower() for name in names}

        source_pm_missing[i] = any(
            name in normalized
            for name in ("pm_missing", "missing_pm", "pm_invalid")
        )

        source_pm_startup[i] = any(
            name in normalized
            for name in (
                "pm_settling",
                "sps30_not_ready",
                "pm_not_ready",
                "pm_warmup",
                "pm_warming",
            )
        )

        source_sensor_fault[i] = any(
            name in normalized
            for name in (
                "sensor_fault",
                "pm_sensor_fault",
                "invalid_sensor",
                "sensor_error",
            )
        )

        source_clock_unsynced[i] = any(
            "clock_unsynced" in name or "timestamp_missing_no_wall_clock" in name
            for name in normalized
        )

        source_spike[i] = "spike" in normalized or "pm_spike" in normalized

    mark(source_pm_missing, QualityFlag.MISSING)
    mark(source_pm_startup, QualityFlag.STARTUP)
    mark(source_sensor_fault, QualityFlag.SENSOR_FAULT)
    mark(source_clock_unsynced, QualityFlag.CLOCK_UNSYNCED)

    # A generic review flag is retained as provenance, but it is not by itself
    # a PM exclusion: e.g. invalid pressure metadata does not invalidate PM.
    # Explicit PM-specific problems are handled above.
    source_review = source_quality.eq("review").to_numpy(copy=True)

    # Detect device-level sensor faults and PM-specific faults.
    for i, names in enumerate(source_names):
        if _has_token(
            names,
            ("sensor_fault", "invalid_sensor", "sensor_error", "pm_missing"),
        ):
            source_review[i] = True

    mark(source_review, QualityFlag.SOURCE_REVIEW)

    # Gas readiness is an independent eligibility dimension.
    if "sgp41_state" in df:
        gas_quality_ok = gas_state.isin(gas_ready_states)
    else:
        # If state is unavailable, the code cannot certify gas readiness.
        gas_quality_ok = pd.Series(False, index=df.index)

    df["gas_quality_ok"] = gas_quality_ok.to_numpy()

    # Restart handling: operate on each contiguous boot segment separately.
    if "boot_id" in df:
        boot = df["boot_id"].astype("string")
        previous_boot = boot.shift(1)
        changed = (
            boot.notna()
            & previous_boot.notna()
            & boot.ne(previous_boot)
        )

        uptime = numeric_column("uptime_s")
        restart_indices = np.flatnonzero(changed.to_numpy())

        for position, start in enumerate(restart_indices):
            end = (
                restart_indices[position + 1]
                if position + 1 < len(restart_indices)
                else n
            )

            segment_uptime = uptime.iloc[start:end]
            warmup = (
                segment_uptime.notna()
                & segment_uptime.ge(0)
                & segment_uptime.le(restart_warmup_s)
            )
            local_indices = np.arange(start, end)[warmup.to_numpy()]
            flags[local_indices] |= int(QualityFlag.RESTART)

    # Robust local spike detector. This uses neighboring observations and is
    # retrospective, not a causal online detector.
    if spike_window_samples >= 3 and n >= 3:
        window = int(spike_window_samples)
        minimum = max(3, window // 2)

        rolling_median = pm.rolling(
            window,
            center=True,
            min_periods=minimum,
        ).median()

        deviation = (pm - rolling_median).abs()
        rolling_mad = deviation.rolling(
            window,
            center=True,
            min_periods=minimum,
        ).median()

        threshold = (
            spike_n_sigma
            * 1.4826
            * rolling_mad.clip(lower=0.5)
        )
        spike = deviation.gt(threshold) & deviation.notna()

        mark(spike, QualityFlag.SPIKE)

    if source_spike.any():
        mark(source_spike, QualityFlag.SPIKE)

    # Conservative flatline diagnostic across all available PM channels.
    pm_columns = [
        col for col in ("pm1", "pm2_5", "pm4", "pm10")
        if col in df
    ]

    if (
        len(pm_columns) >= 2
        and flatline_samples >= 2
        and n >= flatline_samples
    ):
        block = df[pm_columns].apply(pd.to_numeric, errors="coerce")

        rolling_max = block.rolling(
            flatline_samples,
            min_periods=flatline_samples,
        ).max()
        rolling_min = block.rolling(
            flatline_samples,
            min_periods=flatline_samples,
        ).min()

        # Only classify a window as flat when every available PM channel
        # remains exactly constant throughout the full window.
        flat_end = (rolling_max - rolling_min).eq(0).all(axis=1)

        flat_mask = np.zeros(n, dtype=bool)
        for end_pos in np.flatnonzero(flat_end.to_numpy()):
            flat_mask[
                end_pos - flatline_samples + 1 : end_pos + 1
            ] = True

        mark(flat_mask, QualityFlag.FLATLINE)

    df["quality_flags_int"] = flags
    df["quality_flags"] = [
        [
            flag.name.lower()
            for flag in QualityFlag
            if flag != QualityFlag.OK and value & int(flag)
        ]
        for value in flags
    ]

    # PM eligibility excludes measurement problems and startup/restart states.
    # It intentionally does not exclude a sample solely because it is a spike,
    # has unsynchronized wall-clock time, or has unrelated metadata problems.
    pm_hard_flags = int(
        QualityFlag.MISSING
        | QualityFlag.OUT_OF_RANGE
        | QualityFlag.FLATLINE
        | QualityFlag.RESTART
        | QualityFlag.SENSOR_FAULT
        | QualityFlag.STARTUP
    )

    pm_quality_ok = (flags & pm_hard_flags) == 0

    # Keep the historical field for existing aggregation code.
    df["pm_quality_ok"] = pm_quality_ok
    df["quality_ok"] = pm_quality_ok

    df["strict_quality_ok"] = (
        pm_quality_ok
        & ((flags & int(QualityFlag.SPIKE)) == 0)
    )

    # Time quality is separate from PM measurement quality.
    timestamp = pd.to_datetime(
        df.get("timestamp", pd.Series(pd.NaT, index=df.index)),
        utc=True,
        errors="coerce",
    )
    df["time_quality_ok"] = (
        timestamp.notna()
        & ((flags & int(QualityFlag.CLOCK_UNSYNCED)) == 0)
    ).to_numpy()

    df["quality_downgraded"] = (
        (flags & int(QualityFlag.HUMIDITY)) != 0
    )

    return df
