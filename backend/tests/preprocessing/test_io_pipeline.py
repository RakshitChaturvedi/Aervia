import json
from pathlib import Path

import pandas as pd

from src.preprocessing.io import load_records
from src.preprocessing.pipeline import PreprocessConfig, preprocess_dataset


def test_load_replay_jsonl_preserves_untimestamped_records(tmp_path: Path):
    path = tmp_path / "sensor.jsonl"
    rows = [
        {"timestamp": None, "stream": "sensor", "sequence": 1, "uptime_s": 5.0,
         "pm2_5": 20.0, "pm10": 30.0, "raw_payload": {"timestamp_ist": "", "pm2_5_ug_m3": "20"}},
        {"timestamp": "2026-10-09T10:00:01+00:00", "stream": "sensor", "sequence": 2,
         "pm2_5": 22.0, "pm10": 32.0, "raw_payload": {"pm2_5_ug_m3": "22"}},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    frame = load_records(path)
    assert len(frame) == 2
    assert frame["timestamp"].isna().sum() == 1
    assert frame.loc[0, "sequence"] == 1


def test_pipeline_writes_expected_outputs_and_does_not_fabricate_time(tmp_path: Path):
    input_path = tmp_path / "sensor.jsonl"
    rows = []
    for i in range(180):
        rows.append({
            "timestamp": None if i < 3 else (pd.Timestamp("2026-10-09T10:00:00Z") + pd.Timedelta(seconds=i)).isoformat(),
            "stream": "sensor", "sequence": i + 1, "uptime_s": i,
            "pm2_5": 20 + (i % 10), "pm10": 30 + (i % 10),
            "quality_flag": "review" if i < 3 else "ok",
            "quality_flags": ["clock_unsynced"] if i < 3 else [],
            "raw_payload": {"pm2_5_ug_m3": str(20 + (i % 10))},
        })
    input_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    output = tmp_path / "processed"
    result = preprocess_dataset(input_path, output, PreprocessConfig(
        baseline_window_min=5, baseline_min_valid_fraction=0.2,
        min_valid_fraction_per_minute=0.1, spike_window_samples=3, flatline_samples=20,
    ))
    assert len(result.samples) == 180
    assert result.summary["samples_untimestamped"] == 3
    assert (output / "aligned" / "samples.csv").exists()
    assert (output / "minute" / "minute.csv").exists()
    assert (output / "five_minute" / "five_minute.csv").exists()
    assert (output / "aligned" / "exclusions.csv").exists()
    assert (output / "manifest.json").exists()