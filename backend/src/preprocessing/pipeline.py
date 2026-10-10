"""Dataset-level preprocessing orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import pandas as pd

from .aggregation import minute_table, five_minute_table
from .baseline import add_baseline_features
from .io import load_records, write_table
from .quality import flag_samples


@dataclass(frozen=True)
class PreprocessConfig:
    timezone: str = "Asia/Kolkata"
    pm_min: float = 0.0
    pm_max: float = 1000.0
    humidity_unreliable_pct: float = 90.0
    flatline_samples: int = 120
    spike_window_samples: int = 15
    spike_n_sigma: float = 5.0
    restart_warmup_s: float = 60.0
    min_valid_fraction_per_minute: float = 0.8
    min_valid_fraction_per_five_minutes: float = 0.8
    baseline_window_min: int = 20
    baseline_percentile: float = 10.0
    baseline_causal: bool = True
    baseline_min_valid_fraction: float = 0.5
    baseline_mature_valid_fraction: float = 0.8


@dataclass
class PreprocessedDataset:
    samples: pd.DataFrame
    minute: pd.DataFrame
    five_minute: pd.DataFrame
    exclusions: pd.DataFrame
    summary: dict = field(default_factory=dict)


def _exclusions(samples: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in samples.iterrows():
        reasons = row.get("quality_flags", [])
        if not isinstance(reasons, list):
            reasons = []
        if pd.isna(row.get("timestamp")):
            reasons = list(reasons) + ["timestamp_missing_no_wall_clock"]
        if not bool(row.get("quality_ok", False)):
            rows.append({
                "input_order": row.get("_input_order"),
                "timestamp": row.get("timestamp"),
                "sequence": row.get("sequence"),
                "uptime_s": row.get("uptime_s"),
                "device_id": row.get("device_id"),
                "boot_id": row.get("boot_id"),
                "eligible_for_pm_analysis": False,
                "reasons": "|".join(dict.fromkeys(reasons)) or "quality_not_ok",
            })
        elif pd.isna(row.get("timestamp")):
            rows.append({
                "input_order": row.get("_input_order"),
                "timestamp": row.get("timestamp"),
                "sequence": row.get("sequence"),
                "uptime_s": row.get("uptime_s"),
                "device_id": row.get("device_id"),
                "boot_id": row.get("boot_id"),
                "eligible_for_pm_analysis": False,
                "reasons": "|".join(dict.fromkeys(reasons)),
            })
    return pd.DataFrame(rows, columns=[
        "input_order", "timestamp", "sequence", "uptime_s", "device_id",
        "boot_id", "eligible_for_pm_analysis", "reasons",
    ])


def preprocess_dataset(input_path: str | Path, output_dir: str | Path | None = None,
                       config: PreprocessConfig | None = None) -> PreprocessedDataset:
    cfg = config or PreprocessConfig()
    raw = load_records(input_path)
    if raw.empty:
        raise ValueError(f"No records found in {input_path}")
    samples = flag_samples(
        raw, pm_range=(cfg.pm_min, cfg.pm_max),
        humidity_unreliable_pct=cfg.humidity_unreliable_pct,
        flatline_samples=cfg.flatline_samples,
        spike_window_samples=cfg.spike_window_samples,
        spike_n_sigma=cfg.spike_n_sigma,
        restart_warmup_s=cfg.restart_warmup_s,
    )
    # Do not sort all untimestamped records ahead of timed ones: preserve source order
    # and let the time-based aggregation use only rows with real timestamps.
    minute = minute_table(samples, min_valid_fraction=cfg.min_valid_fraction_per_minute)
    if not minute.empty:
        minute = add_baseline_features(
            minute, window_min=cfg.baseline_window_min,
            percentile=cfg.baseline_percentile, causal=cfg.baseline_causal,
            min_valid_fraction=cfg.baseline_min_valid_fraction,
            mature_valid_fraction=cfg.baseline_mature_valid_fraction
        )
    five = five_minute_table(minute, min_valid_fraction=cfg.min_valid_fraction_per_five_minutes)
    exclusions = _exclusions(samples)
    summary = {
        "input_path": str(input_path),
        "samples_total": int(len(samples)),
        "samples_timestamped": int(samples["timestamp"].notna().sum()),
        "samples_untimestamped": int(samples["timestamp"].isna().sum()),
        "samples_quality_ok": int(samples["quality_ok"].sum()),
        "samples_quality_excluded": int((~samples["quality_ok"]).sum()),
        "minute_bins": int(len(minute)),
        "five_minute_bins": int(len(five)),
        "baseline_window_min": cfg.baseline_window_min,
        "baseline_percentile": cfg.baseline_percentile,
        "baseline_causal": cfg.baseline_causal,
        "baseline_min_valid_fraction": cfg.baseline_min_valid_fraction,
        "baseline_mature_valid_fraction": cfg.baseline_mature_valid_fraction,
        "note": "Untimestamped records are retained but never assigned fabricated wall-clock timestamps. No interpolation or humidity correction is applied.",
    }
    result = PreprocessedDataset(samples, minute, five, exclusions, summary)
    if output_dir is not None:
        assert len(samples) == (
            summary["samples_timestamped"]
            + summary["samples_untimestamped"]
        )
        assert summary["samples_total"] == len(samples)
        save_dataset(result, output_dir, cfg)
    return result


def save_dataset(dataset: PreprocessedDataset, output_dir: str | Path, config: PreprocessConfig) -> None:
    root = Path(output_dir)
    write_table(dataset.samples, root / "aligned" / "samples.csv")
    write_table(dataset.minute, root / "minute" / "minute.csv")
    write_table(dataset.five_minute, root / "five_minute" / "five_minute.csv")
    write_table(dataset.exclusions, root / "aligned" / "exclusions.csv")
    (root / "manifest.json").write_text(json.dumps({
        "summary": dataset.summary,
        "config": config.__dict__,
        "outputs": [
            "aligned/samples.csv", "aligned/exclusions.csv",
            "minute/minute.csv", "five_minute/five_minute.csv",
        ],
    }, indent=2, default=str), encoding="utf-8")