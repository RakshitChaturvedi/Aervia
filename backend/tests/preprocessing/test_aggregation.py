import pandas as pd

from src.preprocessing.aggregation import minute_table, five_minute_table


def test_minute_aggregation_keeps_empty_time_bins_as_gaps():
    timestamps = pd.to_datetime([
        "2026-10-09T10:00:01Z", "2026-10-09T10:00:02Z",
        "2026-10-09T10:02:01Z", "2026-10-09T10:02:02Z",
    ])
    frame = pd.DataFrame({"timestamp": timestamps, "pm2_5": [10, 12, 30, 32],
                          "quality_ok": [True] * 4, "quality_downgraded": [False] * 4})
    out = minute_table(frame, min_valid_fraction=0.5)
    assert len(out) == 3
    assert pd.isna(out.loc[1, "pm2_5"])
    assert out.loc[1, "sample_count"] == 0
    assert not out.loc[1, "quality_ok"]


def test_five_minute_table_summarizes_minute_bins():
    minute = pd.DataFrame({
        "timestamp": pd.date_range("2026-10-09T10:00:00Z", periods=5, freq="min"),
        "pm2_5": [10, 20, 30, 40, 50],
        "quality_ok": [True] * 5,
    })
    out = five_minute_table(minute)
    assert len(out) == 1
    assert out.loc[0, "pm2_5"] == 30
    assert out.loc[0, "valid_minute_count"] == 5