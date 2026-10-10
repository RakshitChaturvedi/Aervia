from __future__ import annotations
from typing import Any


def _num(value: Any) -> float | None:
    try:
        n = float(value)
        return n if n == n and abs(n) != float("inf") else None
    except (TypeError, ValueError):
        return None


def select_recommendations(context: dict[str, Any], language: str = "en", max_actions: int = 4) -> dict[str, Any]:
    w = context.get("warning") or {}
    severity = str(w.get("severity", "UNKNOWN")).upper()
    lifecycle = str(w.get("lifecycle", "UNKNOWN")).upper()
    gas_readiness = str(w.get("current_gas_readiness", "UNKNOWN")).upper()
    peak = _num(w.get("peak_pm2_5_ug_m3"))
    excess = _num(w.get("peak_excess_pm2_5_ug_m3"))
    duration = _num(w.get("duration_elapsed_minutes"))
    coverage = _num(w.get("coverage_fraction"))
    actions: list[dict[str, Any]] = []

    def add(action_id: str, title: str, instruction: str, rationale: str, urgency: str = "ROUTINE", refs: list[str] | None = None) -> None:
        actions.append({"action_id": action_id, "title": title, "instruction": instruction, "rationale": rationale, "urgency": urgency, "audience": "SITE_OPERATOR", "evidence_refs": refs or []})

    if severity in {"SEVERE", "CRITICAL"}:
        add("inspect_local_area", "Inspect the immediate area", "Have the site operator check for nearby activities or conditions that could coincide with the elevated reading, without assuming a source.", "The warning is classified as severe by the configured prototype rules.", "HIGH", ["warning.severity", "warning.peak_excess_pm2_5_ug_m3"])
        add("verify_followup_readings", "Verify subsequent readings", "Check the next valid sensor readings and confirm whether PM2.5 remains elevated or begins to decline.", "Follow-up measurements are needed to determine whether the event persists.", "HIGH", ["warning.peak_pm2_5_ug_m3", "warning.lifecycle"])
    elif severity == "ELEVATED":
        add("review_elevated_reading", "Review the elevated reading", "Review the event and inspect the immediate monitoring area for relevant activity; do not assign a pollution source from this reading alone.", "The event exceeded the configured elevated-priority threshold.", "HIGH", ["warning.severity", "warning.peak_excess_pm2_5_ug_m3"])
        add("check_next_readings", "Check the next readings", "Review subsequent valid measurements to see whether the elevation persists or recovers.", "The event's persistence and recovery affect the appropriate response.", "ROUTINE", ["warning.lifecycle", "warning.end_utc"])
    elif severity == "WATCH":
        add("monitor_trend", "Monitor the trend", "Continue monitoring and review the next valid readings before escalating the response.", "The measured increase crossed the configured watch threshold.", "ROUTINE", ["warning.severity", "warning.peak_excess_pm2_5_ug_m3"])
    else:
        add("review_data_quality", "Review available measurements", "Check sensor quality and readiness before drawing conclusions from this record.", "The warning does not contain a recognized severity category.", "ROUTINE", ["warning.severity"])

    if lifecycle == "OPEN_AT_CAPTURE_END":
        add("confirm_current_state", "Confirm current conditions", "The recording ended during this event. Obtain a new measurement before treating the event as currently active or resolved.", "The capture boundary does not establish the live state.", "HIGH", ["warning.lifecycle", "warning.end_utc"])
    if coverage is not None and coverage < 0.7:
        add("validate_low_coverage", "Validate limited data coverage", "Treat this result as provisional and inspect missing or quality-excluded observations before taking consequential action.", "The event has less than 70% eligible coverage.", "ROUTINE", ["warning.coverage_fraction"])
    if gas_readiness not in {"READY", "OK", "GAS_READY"}:
        add("note_gas_unavailable", "Do not infer gas conditions", "Do not infer that gases are absent or safe from this event; gas measurements are not currently ready for interpretation.", "Gas readiness is reported as unavailable or not ready.", "ROUTINE", ["warning.current_gas_readiness"])

    uncertainty = ["A single monitoring node does not establish conditions across the campus.", "This event does not identify the pollution source.", "Severity is a prototype triage category, not an official AQI category or medical-risk assessment."]
    if lifecycle == "OPEN_AT_CAPTURE_END":
        uncertainty.append("The recording ended during the event; current continuation or recovery is unknown.")
    if gas_readiness not in {"READY", "OK", "GAS_READY"}:
        uncertainty.append("Gas measurements are not ready for interpretation; this is not evidence that gases are absent.")
    if context.get("parameter_context", {}).get("particle_distribution_interpretable") is False:
        uncertainty.append("Particle-distribution interpretation is not validated for this dataset.")
    if coverage is not None and coverage < 0.7:
        uncertainty.append("Limited event coverage reduces confidence in the event summary.")

    evidence = []
    for key, label, unit in (("severity", "Warning severity", None), ("peak_pm2_5_ug_m3", "Peak PM2.5", "µg/m³"), ("peak_baseline_pm2_5_ug_m3", "Estimated baseline PM2.5", "µg/m³"), ("peak_excess_pm2_5_ug_m3", "Peak excess over baseline", "µg/m³"), ("duration_elapsed_minutes", "Observed event duration", "minutes"), ("coverage_fraction", "Eligible coverage fraction", None), ("lifecycle", "Event lifecycle", None)):
        if w.get(key) is not None:
            evidence.append({"field": key, "label": label, "value": w[key], "unit": unit, "source": "layer_4_warning"})
    if peak is not None and peak < 0:
        uncertainty.append("The supplied peak measurement is outside the expected non-negative range; verify the input.")
    if excess is None:
        uncertainty.append("Peak excess over baseline is unavailable; recommendations are based on the warning category only.")
    if duration is not None and duration < 0:
        uncertainty.append("Event duration is invalid; verify the warning input.")
    return {"actions": actions[:max_actions], "uncertainty": list(dict.fromkeys(uncertainty)), "evidence": evidence}