from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from .config import WarningConfig


USABLE_STATUSES = {"OK", "PARTIAL"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _num(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _severity(excess: float, duration: float, coverage: float, cfg: WarningConfig) -> tuple[str, int, list[str]]:
    reasons: list[str] = []
    if excess >= cfg.severe_excess_ug_m3:
        level = "SEVERE"
        score = 80
        reasons.append("peak excess crossed the prototype severe-priority threshold")
    elif excess >= cfg.elevated_excess_ug_m3:
        level = "ELEVATED"
        score = 60
        reasons.append("peak excess crossed the prototype elevated-priority threshold")
    elif excess >= cfg.watch_excess_ug_m3:
        level = "WATCH"
        score = 35
        reasons.append("peak excess crossed the prototype watch threshold")
    else:
        level = "INFORMATIONAL"
        score = 15
        reasons.append("event met the Layer 3B event detector but remained below the warning watch threshold")

    if duration >= cfg.elevated_duration_min:
        score = min(100, score + 10)
        reasons.append("event persisted for at least the configured duration threshold")
    if coverage < cfg.low_coverage_cutoff:
        score = max(0, score - 20)
        reasons.append("reduced event coverage lowered confidence")
    return level, score, reasons


def build_warnings(
    event_doc: dict[str, Any],
    recovery_doc: dict[str, Any] | None = None,
    exposure_doc: dict[str, Any] | None = None,
    features_rows: list[dict[str, Any]] | None = None,
    config: WarningConfig | None = None,
    dataset_id: str | None = None,
) -> dict[str, Any]:
    """Convert Layer 3B findings into explainable, conservative warning records."""
    cfg = config or WarningConfig()
    event_status = str(event_doc.get("status", "UNKNOWN"))
    events = event_doc.get("results") or []
    if event_status not in USABLE_STATUSES or not isinstance(events, list):
        events = []

    recoveries = {str(r.get("event_id")): r for r in (recovery_doc or {}).get("results", []) if r.get("event_id")}
    exposures = {str(r.get("window_id")): r for r in (exposure_doc or {}).get("results", []) if r.get("window_id")}
    feature_rows = features_rows or []
    warnings = []

    for event in events:
        event_id = str(event.get("event_id") or "unknown-event")
        excess = _num(event.get("peak_excess_pm2_5_ug_m3"))
        duration = _num(event.get("duration_elapsed_minutes")) or 0.0
        coverage = _num(event.get("coverage_fraction"))
        if excess is None:
            warnings.append({
                "warning_id": f"{event_id}:warning", "event_id": event_id,
                "status": "SUPPRESSED_INSUFFICIENT_EVIDENCE", "severity": "UNASSESSED",
                "priority_score": None, "reasons": ["peak excess is missing or non-numeric"],
            })
            continue
        coverage = coverage if coverage is not None else 0.0
        level, score, reasons = _severity(excess, duration, coverage, cfg)
        if coverage < cfg.minimum_event_coverage:
            status = "DEGRADED_CONFIDENCE"
            reasons.append("event coverage is below the configured minimum")
        else:
            status = "ISSUED"

        if int(event.get("quality_downgraded_candidate_count") or 0) > 0:
            score = max(0, score - 10)
            reasons.append("one or more candidate observations had downgraded quality")

        boundary_end = bool(event.get("boundary_at_capture_end"))
        lifecycle = "OPEN_AT_CAPTURE_END" if boundary_end else "OBSERVED_EVENT"
        if boundary_end:
            reasons.append("event reaches the end of the available capture; live continuation is unknown")

        recovery = recoveries.get(event_id)
        recovery_status = recovery.get("recovery_status") if recovery else None
        if recovery_status == "RECOVERY_NOT_OBSERVED":
            reasons.append("recovery was not observed within the available follow-up window")
        elif recovery_status == "FOLLOWUP_INCOMPLETE":
            reasons.append("recovery follow-up is incomplete")

        exposure = exposures.get(event_id)
        exposure_integral = _num((exposure or {}).get("positive_excess_time_integral_ug_h_m3"))
        if exposure and str(exposure.get("status", "OK")) not in USABLE_STATUSES:
            exposure_integral = None

        # Current readiness is diagnostic context only; it does not erase an earlier PM event.
        latest_gas_status = None
        latest_quality = None
        if feature_rows:
            last = feature_rows[-1]
            latest_gas_status = last.get("gas_interpretation_status") or last.get("gas_status")
            latest_quality = last.get("parameter_feature_status")

        warnings.append({
            "warning_id": f"{event_id}:warning",
            "event_id": event_id,
            "status": status,
            "severity": level,
            "priority_score": score,
            "warning_type": "PM2_5_EVENT",
            "pollutant": "PM2.5",
            "start_utc": event.get("start_utc"),
            "end_utc": event.get("end_utc"),
            "peak_utc": event.get("peak_utc"),
            "peak_pm2_5_ug_m3": _num(event.get("peak_pm2_5_ug_m3")),
            "peak_baseline_pm2_5_ug_m3": _num(event.get("peak_baseline_pm2_5_ug_m3")),
            "peak_excess_pm2_5_ug_m3": excess,
            "mean_excess_pm2_5_ug_m3": _num(event.get("mean_excess_pm2_5_ug_m3")),
            "duration_elapsed_minutes": duration,
            "coverage_fraction": coverage,
            "lifecycle": lifecycle,
            "recovery_status": recovery_status,
            "positive_excess_integral_ug_h_m3": exposure_integral,
            "current_gas_readiness": latest_gas_status,
            "latest_parameter_feature_status": latest_quality,
            "reasons": reasons,
            "limitations": [
                "Severity is a configurable prototype triage category, not an official AQI category or medical-risk assessment.",
                "A single node does not establish conditions across the campus or identify the pollution source.",
                "A concentration-time integral is not personal inhaled dose or population exposure.",
            ],
        })

    warnings.sort(key=lambda x: (x.get("priority_score") if x.get("priority_score") is not None else -1,
                                 x.get("start_utc") or ""), reverse=True)
    eligible = [w for w in warnings if w.get("status") in {"ISSUED", "DEGRADED_CONFIDENCE"}]
    overall = "OK" if event_status in USABLE_STATUSES else "PARTIAL"
    if event_status not in USABLE_STATUSES:
        top_notes = [f"Layer 3B event detector status was {event_status}; event warnings were not issued."]
    else:
        top_notes = ["Warnings are rule-based prototype triage outputs; thresholds require later calibration."]

    source_fingerprint = _fingerprint({
        "events": events,
        "recovery_status": (recovery_doc or {}).get("status"),
        "exposure_status": (exposure_doc or {}).get("status"),
    })
    return {
        "layer": "4",
        "module": "warning_engine",
        "status": overall,
        "algorithm_version": cfg.version,
        "generated_at_utc": _utc_now(),
        "dataset_id": dataset_id or (event_doc.get("provenance") or {}).get("dataset_id"),
        "input_statuses": {
            "event_detection": event_status,
            "recovery_profile": (recovery_doc or {}).get("status", "NOT_PROVIDED"),
            "exposure_burden": (exposure_doc or {}).get("status", "NOT_PROVIDED"),
        },
        "config": cfg.as_dict(),
        "input_fingerprint": source_fingerprint,
        "warning_count": len(warnings),
        "issued_warning_count": len(eligible),
        "warnings": warnings,
        "notes": top_notes,
        "limitations": [
            "Prototype thresholds are not regulatory or health thresholds.",
            "No source attribution is performed.",
            "No live state is inferred from historical capture boundaries.",
            "Gas and particle-distribution features are not used to increase severity unless their interpretation is validated.",
        ],
    }