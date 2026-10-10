import pandas as pd

from src.preprocessing.quality import QualityFlag, flag_samples


def test_missing_pm_is_flagged_but_retained():
    frame = pd.DataFrame({"pm2_5": [10.0, None], "timestamp": pd.to_datetime(
        ["2026-10-09T10:00:00Z", "2026-10-09T10:00:01Z"])})
    out = flag_samples(frame, spike_window_samples=3, flatline_samples=10)
    assert len(out) == 2
    assert bool(out.loc[1, "quality_flags_int"] & int(QualityFlag.MISSING))
    assert not out.loc[1, "quality_ok"]


def test_unsynced_startup_and_review_flags_are_ineligible():
    frame = pd.DataFrame({
        "pm2_5": [20.0, 21.0, 22.0],
        "source_quality_flag": ["ok", "review", "ok"],
        "source_quality_flags": [[], ["clock_unsynced", "pm_settling"], []],
    })
    out = flag_samples(frame, spike_window_samples=3, flatline_samples=10)
    assert out.loc[0, "quality_ok"]
    assert not out.loc[1, "quality_ok"]
    assert "clock_unsynced" in out.loc[1, "quality_flags"]
    assert "startup" in out.loc[1, "quality_flags"]