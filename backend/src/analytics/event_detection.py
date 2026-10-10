import pandas as pd
from .schemas import AnalysisStatus
from .common import normalize_features, eligible_mask, make_result, as_bool
from .config import EventDetectionConfig

REQUIRED = {"timestamp", "pm2_5", "baseline_pm2_5", "pm2_5_excess", "analysis_ok"}

def detect_events(features, config=None, dataset_id="unspecified"):
    cfg = config or EventDetectionConfig()
    df, error = normalize_features(features, REQUIRED)
    if error:
        empty = pd.DataFrame(columns=["timestamp"])
        return make_result("event_detection", AnalysisStatus.FAILED_VALIDATION, empty, dataset_id,
                           cfg.__dict__, [], {}, [error], exclusions=[error])
    if cfg.persistence_minutes < 1 or cfg.gap_tolerance_minutes < 0 or not 0 <= cfg.minimum_coverage_fraction <= 1:
        return make_result("event_detection", AnalysisStatus.FAILED_VALIDATION, df, dataset_id,
                           cfg.__dict__, [], {}, ["Invalid event configuration."])
    for col in ("pm2_5", "baseline_pm2_5", "pm2_5_excess"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    eligible = eligible_mask(df, "pm2_5_excess") & df["baseline_pm2_5"].notna() & df["pm2_5"].notna()
    downgraded = as_bool(df["quality_downgraded"]) if "quality_downgraded" in df else pd.Series(False, index=df.index)
    candidate = eligible & (df["pm2_5_excess"] >= cfg.excess_threshold_ug_m3)
    if cfg.concentration_threshold_ug_m3 is not None:
        candidate &= df["pm2_5"] >= cfg.concentration_threshold_ug_m3
    ids = list(df.index[candidate]); groups = []
    if ids:
        group = [ids[0]]
        for idx in ids[1:]:
            gap = (df.loc[idx, "timestamp"] - df.loc[group[-1], "timestamp"]).total_seconds()/60
            if gap <= cfg.gap_tolerance_minutes + 1: group.append(idx)
            else: groups.append(group); group = [idx]
        groups.append(group)
    events = []
    for group in groups:
        if len(group) < cfg.persistence_minutes: continue
        a, b = df.loc[group[0], "timestamp"], df.loc[group[-1], "timestamp"]
        duration = (b-a).total_seconds()/60 + 1
        window = df[(df.timestamp >= a) & (df.timestamp <= b)]
        win_eligible = eligible.loc[window.index]
        coverage = float(win_eligible.sum()/max(1, int(duration)))
        if int(win_eligible.sum()) < cfg.minimum_eligible_minutes or coverage < cfg.minimum_coverage_fraction:
            boundary_status = "UNCERTAIN_COVERAGE"
        else: boundary_status = "ADEQUATE_COVERAGE"
        segment = df.loc[group]; peak = segment.loc[segment["pm2_5_excess"].idxmax()]
        support = {}
        for col in ("pm1_to_pm2_5_band", "pm2_5_to_pm4_band", "pm4_to_pm10_band",
                    "particle_distribution_status", "particle_distribution_interpretable"):
            if col in peak.index and pd.notna(peak[col]): support[col] = peak[col]
        events.append({
            "event_id": f"{dataset_id}:PM25:{len(events)+1:04d}",
            "start_utc": a.isoformat(), "end_utc": b.isoformat(),
            "boundary_at_capture_start": bool(a == df.timestamp.iloc[0]),
            "boundary_at_capture_end": bool(b == df.timestamp.iloc[-1]),
            "duration_elapsed_minutes": float((b-a).total_seconds()/60),
            "duration_inclusive_grid_minutes": float(duration),
            "candidate_observations": len(group), "expected_grid_minutes": int(duration),
            "eligible_minutes_in_window": int(win_eligible.sum()), "coverage_fraction": coverage,
            "peak_utc": peak.timestamp.isoformat(), "peak_pm2_5_ug_m3": float(peak.pm2_5),
            "peak_baseline_pm2_5_ug_m3": float(peak.baseline_pm2_5),
            "peak_excess_pm2_5_ug_m3": float(peak.pm2_5_excess),
            "mean_excess_pm2_5_ug_m3": float(segment.pm2_5_excess.mean()),
            "quality_downgraded_candidate_count": int(downgraded.loc[group].sum()),
            "boundary_quality": boundary_status, "supporting_parameter_features": support,
        })
    status = AnalysisStatus.OK if events or eligible.any() else AnalysisStatus.INSUFFICIENT_DATA
    return make_result("event_detection", status, df, dataset_id, cfg.__dict__, events,
        {"pm2_5": "µg/m³", "pm2_5_excess": "µg/m³", "duration": "min"},
        ["Thresholds are provisional exploratory defaults, not validated alert thresholds.",
         "Bridged gaps are not counted as observed candidate minutes.",
         "Events touching capture boundaries may be censored.",
         "Particle-distribution features are supporting observations, not source labels."],
        eligible=eligible, exclusions=[f"ineligible_pm_rows={int((~eligible).sum())}"],
        valid_outputs=["event boundaries", "peak/mean excess", "coverage", "supporting features"] if events else [])