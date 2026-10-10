
"""Causal trailing baseline and excess PM features."""

from __future__ import annotations

import math

import pandas as pd


def rolling_baseline(
    concentration: pd.Series,
    *,
    window_min: int = 20,
    percentile: float = 10.0,
    causal: bool = True,
    min_valid_fraction: float = 0.5,
) -> pd.Series:
    """Calculate a time-based rolling percentile baseline.

    In causal mode, the current observation is excluded from its own baseline.
    Input must be a one-minute series with a DatetimeIndex.

    This function returns a provisional baseline whenever the minimum number
    of valid observations exists. Maturity is computed separately by
    add_baseline_features().
    """
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be in (0, 100]")
    if window_min < 1:
        raise ValueError("window_min must be >= 1")
    if not 0 < min_valid_fraction <= 1:
        raise ValueError("min_valid_fraction must be in (0, 1]")

    series = pd.to_numeric(concentration, errors="coerce").copy()

    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("concentration must have a DatetimeIndex")

    if series.index.has_duplicates:
        raise ValueError("concentration index must not contain duplicate timestamps")

    series = series.sort_index()

    if series.empty:
        return series.astype(float)

    # Expand to a complete one-minute grid so missing minutes count as missing
    # coverage rather than silently disappearing from a time-based window.
    start = series.index.min().floor("min")
    end = series.index.max().floor("min")
    grid = pd.date_range(start=start, end=end, freq="1min", tz=series.index.tz)
    minute_series = series.copy()
    minute_series.index = minute_series.index.floor("min")

    if minute_series.index.has_duplicates:
        raise ValueError(
            "Multiple observations per minute supplied to rolling_baseline; "
            "aggregate to one value per minute first"
        )

    minute_series = minute_series.reindex(grid)

    minimum_valid = max(
        1,
        math.ceil(window_min * min_valid_fraction),
    )

    source = minute_series.shift(1) if causal else minute_series

    baseline = source.rolling(
        f"{window_min}min",
        min_periods=minimum_valid,
        closed="right" if causal else "both",
    ).quantile(percentile / 100.0)

    # Return only the original timestamps.
    return baseline.reindex(series.index)


def add_baseline_features(
    minute: pd.DataFrame,
    *,
    window_min: int = 20,
    percentile: float = 10.0,
    causal: bool = True,
    min_valid_fraction: float = 0.5,
    mature_valid_fraction: float = 0.8,
) -> pd.DataFrame:
    """Add baseline, excess, coverage, maturity, and analysis eligibility.

    baseline_ready:
        At least the configured minimum valid history is available.

    baseline_mature:
        A full window of elapsed history exists and enough of its expected
        minute bins have valid PM values.

    analysis_ok:
        PM quality is acceptable and the baseline is mature.
    """
    if not 0 < mature_valid_fraction <= 1:
        raise ValueError("mature_valid_fraction must be in (0, 1]")
    if not 0 < min_valid_fraction <= 1:
        raise ValueError("min_valid_fraction must be in (0, 1]")

    if minute.empty or "pm2_5" not in minute:
        return minute.copy()

    if "timestamp" not in minute:
        raise ValueError("minute dataframe must contain a timestamp column")

    out = minute.copy()
    out["timestamp"] = pd.to_datetime(
        out["timestamp"],
        utc=True,
        errors="coerce",
    )
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp")

    if out["timestamp"].duplicated().any():
        raise ValueError("minute dataframe contains duplicate timestamps")

    out = out.reset_index(drop=True)

    pm = pd.to_numeric(out["pm2_5"], errors="coerce")
    indexed = pd.Series(
        pm.to_numpy(),
        index=pd.DatetimeIndex(out["timestamp"]),
        name="pm2_5",
    )

    baseline = rolling_baseline(
        indexed,
        window_min=window_min,
        percentile=percentile,
        causal=causal,
        min_valid_fraction=min_valid_fraction,
    )

    # Compute coverage on a complete one-minute grid.
    start = indexed.index.min().floor("min")
    end = indexed.index.max().floor("min")
    full_grid = pd.date_range(start=start, end=end, freq="1min", tz="UTC")

    grid_pm = indexed.copy()
    grid_pm.index = grid_pm.index.floor("min")
    grid_pm = grid_pm.reindex(full_grid)

    valid = grid_pm.notna().astype(int)

    # Causal baseline statistics use only prior observations.
    if causal:
        valid_source = valid.shift(1, fill_value=0)
    else:
        valid_source = valid

    valid_count = valid_source.rolling(
        f"{window_min}min",
        min_periods=1,
        closed="right" if causal else "both",
    ).sum()

    elapsed_count = pd.Series(1, index=full_grid).rolling(
        f"{window_min}min",
        min_periods=1,
        closed="right" if causal else "both",
    ).sum()

    coverage = (valid_count / float(window_min)).clip(upper=1.0)

    # A baseline is provisionally ready when the minimum valid fraction is met.
    ready = (
        baseline.notna()
        & valid_count.ge(math.ceil(window_min * min_valid_fraction))
        & coverage.ge(min_valid_fraction)
    )

    # Mature only after a full window of elapsed history and sufficient valid
    # measurements across that window.
    elapsed_minutes = (
        indexed.index - indexed.index.min()
    ).total_seconds() / 60.0

    enough_elapsed_history = pd.Series(
        elapsed_minutes >= window_min,
        index=indexed.index,
    )
    mature = (
        baseline.notna()
        & elapsed_count.ge(window_min)
        & valid_count.ge(math.ceil(window_min * mature_valid_fraction))
        & coverage.ge(mature_valid_fraction)
    )

    baseline_by_time = baseline.reindex(pd.DatetimeIndex(out["timestamp"]))
    ready_by_time = ready.reindex(pd.DatetimeIndex(out["timestamp"])).fillna(False)
    mature_by_time = mature.reindex(pd.DatetimeIndex(out["timestamp"])).fillna(False)
    count_by_time = valid_count.reindex(pd.DatetimeIndex(out["timestamp"])).fillna(0)
    coverage_by_time = coverage.reindex(pd.DatetimeIndex(out["timestamp"])).fillna(0)

    out["baseline_pm2_5"] = baseline_by_time.to_numpy()
    out["excess_pm2_5"] = (
        pm.to_numpy() - baseline_by_time.to_numpy()
    )
    out["excess_pm2_5"] = out["excess_pm2_5"].clip(lower=0)

    out["baseline_valid_count"] = count_by_time.to_numpy()
    out["baseline_coverage"] = coverage_by_time.to_numpy()
    out["baseline_ready"] = ready_by_time.to_numpy()
    out["baseline_mature"] = mature_by_time.to_numpy()

    # Retain the existing quality_ok interface.
    pm_quality = out.get(
        "pm_quality_ok",
        out.get("quality_ok", pd.Series(False, index=out.index)),
    )
    pm_quality = pd.Series(pm_quality, index=out.index).fillna(False).astype(bool)

    out["analysis_ok"] = (
        pm_quality
        & out["baseline_mature"]
        & pm.notna()
    )

    return out
