import numpy as np
import pandas as pd
import pytest

from src.parameter_intelligence import FeatureConfig, build_parameter_features
from src.parameter_intelligence.gas_diagnostics import add_gas_diagnostics
from src.parameter_intelligence.particulate import add_particulate_features


def sample_minute(n=8):
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-10-09T08:54:00Z", periods=n, freq="min"),
        "pm1": [5, 5, 6, 6, 7, 7, 8, 8][:n],
        "pm2_5": [10, 10, 12, 12, 14, 14, 16, 16][:n],
        "pm4": [15, 15, 18, 18, 21, 21, 24, 24][:n],
        "pm10": [20, 20, 25, 25, 30, 30, 35, 35][:n],
        "baseline_pm2_5": [9] * n,
        "temperature_c": [30.0] * n,
        "humidity_pct": [50.0] * n,
        "pressure_hpa": [1000.0] * n,
        "voc_index": [100.0] * n,
        "nox_index": [1.0] * n,
        "quality_ok": [True] * n,
    })


def test_pipeline_preserves_rows_and_adds_features():
    source = sample_minute()
    out, manifest = build_parameter_features(source)
    assert len(out) == len(source)
    assert "pm2_5_positive_excess" in out
    assert "pm2_5_to_pm4_band" in out
    assert out["pm2_5_positive_excess"].iloc[0] == 1
    assert manifest["output_rows"] == len(source)
    assert manifest["pm_humidity_correction_applied"] is False


def test_missing_optional_channels_do_not_fail():
    source = sample_minute().drop(columns=["pm1", "pm4", "pm10", "voc_index", "nox_index", "humidity_pct"])
    out, manifest = build_parameter_features(source)
    assert len(out) == len(source)
    assert "pm1_available" in out
    assert out["gas_concentration_estimate_available"].eq(False).all()
    assert manifest["available_particle_count_channels"] == []


def test_negative_size_band_beyond_tolerance_is_flagged_not_clipped():
    frame = pd.DataFrame({"pm1": [20.0], "pm2_5": [10.0], "pm4": [30.0], "pm10": [40.0]})
    out = add_particulate_features(frame, ordering_tolerance=2.0)
    assert np.isnan(out["pm1_to_pm2_5_band"].iloc[0])
    assert not bool(out["pm1_to_pm2_5_band_valid"].iloc[0])


def test_gas_indices_are_never_claimed_as_concentrations():
    frame = pd.DataFrame({"voc_index": [100, 120], "nox_index": [1, 1], "sgp41_state": ["LEARNING", "INDEX_WARMUP"]})
    out = add_gas_diagnostics(frame)
    assert not out["gas_sensor_ready"].any()
    assert not out["gas_concentration_estimate_available"].any()
    assert not out["gas_health_warning_eligible"].any()


def test_duplicate_minute_timestamps_are_rejected():
    source = sample_minute(3)
    source.loc[2, "timestamp"] = source.loc[1, "timestamp"]
    with pytest.raises(ValueError, match="at most one row per timestamp"):
        build_parameter_features(source)


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        FeatureConfig(rolling_window_min=1)