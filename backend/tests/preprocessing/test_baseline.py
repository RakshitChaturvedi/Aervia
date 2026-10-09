import pandas as pd

from src.preprocessing.baseline import rolling_baseline, add_baseline_features


def test_causal_baseline_does_not_use_current_or_future_observation():
    idx = pd.date_range("2026-10-09T10:00:00Z", periods=8, freq="min")
    series = pd.Series([10, 10, 10, 10, 100, 100, 100, 100], index=idx)
    baseline = rolling_baseline(series, window_min=4, percentile=10, causal=True, min_valid_fraction=0.5)
    assert pd.isna(baseline.iloc[0])
    assert baseline.iloc[4] <= 10


def test_excess_is_nonnegative_and_warmup_is_not_analysis_eligible():
    minute = pd.DataFrame({
        "timestamp": pd.date_range("2026-10-09T10:00:00Z", periods=6, freq="min"),
        "pm2_5": [10, 10, 10, 20, 30, 10], "quality_ok": [True] * 6,
    })
    out = add_baseline_features(minute, window_min=3, percentile=10, causal=True,
                                min_valid_fraction=0.5)
    assert (out["excess_pm2_5"].dropna() >= 0).all()
    assert not out.loc[0, "analysis_ok"]