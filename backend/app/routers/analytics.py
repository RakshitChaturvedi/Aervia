import os
import csv
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/analytics", tags=["analytics"])

IST = timezone(timedelta(hours=5, minutes=30), "IST")

def to_ist_time_str(ts_str: str) -> str:
    if not ts_str:
        return ""
    s = str(ts_str).strip()
    if s.endswith(" IST"):
        # e.g. "2026-10-09 16:02:00 IST" -> "16:02"
        return s[11:16] if len(s) >= 16 else s
    try:
        clean = s.replace(" ", "T")
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).strftime("%H:%M")
    except Exception:
        return s[11:16] if len(s) >= 16 else s

def to_ist_full_str(ts_str: str) -> str:
    if not ts_str:
        return ""
    s = str(ts_str).strip()
    if s.endswith(" IST"):
        return s
    try:
        clean = s.replace(" ", "T")
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    except Exception:
        return s

BASE_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_BACKEND_DIR, "data")

# In-memory storage for user-submitted interventions, observations, and warning acknowledgements
_acknowledged_warnings = set()
_interventions: List[Dict[str, Any]] = [
    {
        "id": "INT-001",
        "title": "Engine-off protocol during bus arrival & queuing",
        "owner": "Transport & Security",
        "status": "Proposed",
        "start": "2026-10-10T09:00",
        "end": "2026-10-10T11:00",
        "rationale": "Linked to repeated morning excess peaks at College Gate (E-001, E-002). Tests if idling reduction curtails localized PM excess.",
        "created_at": "2026-10-10T08:00:00Z",
    },
    {
        "id": "INT-002",
        "title": "Relocate visitor waiting queue 30m downwind",
        "owner": "Facilities",
        "status": "Scheduled",
        "start": "2026-10-12T08:30",
        "end": "2026-10-12T10:30",
        "rationale": "Mitigates pedestrian exposure zone adjacent to vehicle ingress during morning peak.",
        "created_at": "2026-10-10T08:15:00Z",
    }
]

_observations: List[Dict[str, Any]] = [
    {
        "id": "OBS-001",
        "time": "2026-10-09T09:28",
        "type": "Bus arrival",
        "count": "2 campus shuttle buses",
        "source": "Gate supervisor",
        "notes": "Buses arrived with continuous engine idling for approx 4 minutes before passenger offload.",
        "created_at": "2026-10-09T09:35:00Z"
    },
    {
        "id": "OBS-002",
        "time": "2026-10-09T10:24",
        "type": "Vehicle queue",
        "count": "8 vehicles in entry queue",
        "source": "Traffic officer",
        "notes": "Delivery truck queue backed up past sensor node during visitor check-in.",
        "created_at": "2026-10-09T10:30:00Z"
    }
]

def _read_json_file(relative_path: str) -> Optional[Dict[str, Any]]:
    full_path = os.path.join(DATA_DIR, relative_path)
    if not os.path.exists(full_path):
        return None
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON {full_path}: {e}")
        return None

@router.get("/overview")
def get_analytics_overview():
    """Returns overview metrics, event summaries, and system analysis readiness status."""
    events_data = _read_json_file("analytics/ft1_final_v2/event_detection.json") or {}
    warnings_data = _read_json_file("warnings/ft1_final_v2/warnings.json") or {}
    exposure_data = _read_json_file("analytics/ft1_final_v2/exposure_burden.json") or {}
    
    events = events_data.get("results", [])
    warnings = warnings_data.get("warnings", [])
    
    peak_pm25 = 0.0
    for ev in events:
        pm = float(ev.get("peak_pm2_5_ug_m3", 0.0))
        if pm > peak_pm25:
            peak_pm25 = pm

    severe_count = sum(1 for w in warnings if w.get("severity") == "SEVERE")
    elevated_count = sum(1 for w in warnings if w.get("severity") == "ELEVATED")

    return {
        "location": "College Gate",
        "dataset_id": "ft1_final_v2",
        "capture_window": "2026-10-09 14:24 to 16:02 IST (99 minute bins)",
        "peak_pm25": round(peak_pm25, 1) if peak_pm25 else 201.5,
        "events_count": len(events),
        "warnings_count": len(warnings),
        "severe_warnings": severe_count,
        "elevated_warnings": elevated_count,
        "gas_ready_observations": 0,
        "analysis_readiness": {
            "parameter_features": {"status": "OK", "label": "OK · 99 rows"},
            "event_detection": {"status": "OK", "label": "OK · 4 events"},
            "recovery_profile": {"status": "PARTIAL", "label": "PARTIAL · boundary limited"},
            "activity_association": {"status": "CONTEXT_MISSING", "label": "Context missing"},
            "intervention_check": {"status": "NOT_RUN", "label": "Not run"}
        }
    }


@router.get("/events")
def get_events():
    """Returns detected events enriched with recovery and linked warning metadata."""
    events_data = _read_json_file("analytics/ft1_final_v2/event_detection.json") or {}
    recovery_data = _read_json_file("analytics/ft1_final_v2/recovery_profile.json") or {}
    exposure_data = _read_json_file("analytics/ft1_final_v2/exposure_burden.json") or {}
    warnings_data = _read_json_file("warnings/ft1_final_v2/warnings.json") or {}

    raw_events = events_data.get("results", [])
    raw_recovery = {r.get("event_id"): r for r in recovery_data.get("results", [])}
    raw_exposure = {r.get("window_id"): r for r in exposure_data.get("results", [])}
    raw_warnings = {w.get("event_id"): w for w in warnings_data.get("warnings", [])}

    enriched_events = []
    for ev in raw_events:
        eid = ev.get("event_id")
        rec = raw_recovery.get(eid, {})
        exp = raw_exposure.get(eid, {})
        war = raw_warnings.get(eid, {})

        # Friendly display ID (e.g. E-004)
        short_id = f"E-{eid.split(':')[-1]}" if eid and ":" in eid else eid

        recovery_label = "Incomplete"
        if rec.get("recovery_status") == "RECOVERY_OBSERVED":
            t = rec.get("recovery_time_from_peak_min")
            recovery_label = f"{int(t)} min" if t else "Observed"

        warning_sev = war.get("severity", "Elevated").capitalize()
        is_ack = war.get("warning_id") in _acknowledged_warnings

        enriched_events.append({
            "event_id": eid,
            "short_id": short_id,
            "start_utc": ev.get("start_utc"),
            "end_utc": ev.get("end_utc"),
            "start_ist": to_ist_time_str(ev.get("start_utc")),
            "end_ist": to_ist_time_str(ev.get("end_utc")),
            "start_full_ist": to_ist_full_str(ev.get("start_utc")),
            "end_full_ist": to_ist_full_str(ev.get("end_utc")),
            "duration_min": ev.get("duration_elapsed_minutes"),
            "peak_utc": ev.get("peak_utc"),
            "peak_ist": to_ist_time_str(ev.get("peak_utc")),
            "peak_full_ist": to_ist_full_str(ev.get("peak_utc")),
            "peak_pm25": round(float(ev.get("peak_pm2_5_ug_m3", 0.0)), 1),
            "peak_baseline": round(float(ev.get("peak_baseline_pm2_5_ug_m3", 0.0)), 1),
            "peak_excess": round(float(ev.get("peak_excess_pm2_5_ug_m3", 0.0)), 1),
            "mean_excess": round(float(ev.get("mean_excess_pm2_5_ug_m3", 0.0)), 1),
            "coverage_fraction": ev.get("coverage_fraction", 1.0),
            "boundary_at_end": ev.get("boundary_at_capture_end", False),
            "lifecycle": war.get("lifecycle", "OBSERVED"),
            "integrated_excess_ug_h_m3": round(float(exp.get("positive_excess_time_integral_ug_h_m3", 0.0)), 3),
            "recovery_status": rec.get("recovery_status", "UNKNOWN"),
            "recovery_label": recovery_label,
            "warning_id": war.get("warning_id"),
            "warning_severity": warning_sev,
            "warning_acknowledged": is_ack,
            "reasons": war.get("reasons", []),
            "limitations": war.get("limitations", []),
            "parameter_features": ev.get("supporting_parameter_features", {})
        })

    return {
        "status": "OK",
        "dataset_id": "ft1_final_v2",
        "events": enriched_events
    }


@router.get("/timeline")
def get_timeline():
    """Returns minute-by-minute time-series from features.csv for charting."""
    csv_path = os.path.join(DATA_DIR, "parameter_intelligence", "ft1_final_v2", "features.csv")
    if not os.path.exists(csv_path):
        return {"rows": []}

    rows = []
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                ts = r.get("timestamp", "")
                short_time = to_ist_time_str(ts)
                full_ist = to_ist_full_str(ts)
                
                rows.append({
                    "timestamp": ts,
                    "timestamp_ist": full_ist,
                    "time": short_time,
                    "pm1": round(float(r["pm1"]), 1) if r.get("pm1") else None,
                    "pm2_5": round(float(r["pm2_5"]), 1) if r.get("pm2_5") else None,
                    "pm4": round(float(r["pm4"]), 1) if r.get("pm4") else None,
                    "pm10": round(float(r["pm10"]), 1) if r.get("pm10") else None,
                    "baseline_pm2_5": round(float(r["baseline_pm2_5"]), 1) if r.get("baseline_pm2_5") else None,
                    "excess_pm2_5": round(float(r["excess_pm2_5"]), 1) if r.get("excess_pm2_5") else None,
                    "temp": round(float(r["temperature_c"]), 1) if r.get("temperature_c") else None,
                    "humidity": round(float(r["humidity_pct"]), 1) if r.get("humidity_pct") else None,
                    "voc_index": float(r["voc_index"]) if r.get("voc_index") else None,
                })
    except Exception as e:
        print(f"Error parsing timeline csv: {e}")

    return {"count": len(rows), "timeline": rows}


@router.get("/warnings")
def get_warnings():
    """Returns warning queue inbox with acknowledgment state."""
    warnings_data = _read_json_file("warnings/ft1_final_v2/warnings.json") or {}
    raw_warnings = warnings_data.get("warnings", [])

    results = []
    for w in raw_warnings:
        wid = w.get("warning_id")
        short_id = f"W-{wid.split(':')[-2]}" if wid and ":" in wid else wid
        eid = w.get("event_id")
        short_eid = f"E-{eid.split(':')[-1]}" if eid and ":" in eid else eid

        results.append({
            "warning_id": wid,
            "short_id": short_id,
            "event_id": eid,
            "short_event_id": short_eid,
            "severity": w.get("severity"),
            "status": "ACKNOWLEDGED" if wid in _acknowledged_warnings else w.get("status", "ISSUED"),
            "acknowledged": wid in _acknowledged_warnings,
            "start_utc": w.get("start_utc"),
            "end_utc": w.get("end_utc"),
            "start_ist": to_ist_time_str(w.get("start_utc")),
            "end_ist": to_ist_time_str(w.get("end_utc")),
            "peak_excess": round(float(w.get("peak_excess_pm2_5_ug_m3", 0.0)), 1),
            "peak_pm25": round(float(w.get("peak_pm2_5_ug_m3", 0.0)), 1),
            "lifecycle": w.get("lifecycle"),
            "coverage_fraction": w.get("coverage_fraction", 1.0),
            "reasons": w.get("reasons", []),
            "limitations": w.get("limitations", []),
            "next_check": "Check gate-side vehicle queue and idling" if w.get("severity") == "SEVERE" else "Review event evidence"
        })

    return {"warnings": results}


@router.post("/warnings/{warning_id}/acknowledge")
def acknowledge_warning(warning_id: str):
    """Marks a warning as acknowledged in-memory."""
    _acknowledged_warnings.add(warning_id)
    return {"status": "OK", "warning_id": warning_id, "acknowledged": True}


@router.get("/exposure")
def get_exposure_ledger():
    """Returns integrated PM excess ledger."""
    exposure_data = _read_json_file("analytics/ft1_final_v2/exposure_burden.json") or {}
    return exposure_data


@router.get("/quality")
def get_data_quality():
    """Returns data quality metrics, channels, and diagnostic flags."""
    manifest_data = _read_json_file("parameter_intelligence/ft1_final_v2/manifest.json") or {}
    
    flags = [
        {"flag": "MISSING", "meaning": "Required channel absent", "handling": "Retain row; exclude from calculations requiring the value."},
        {"flag": "OUT_OF_RANGE", "meaning": "Value outside physical bounds", "handling": "Flag and apply channel-specific eligibility rules."},
        {"flag": "FLATLINE", "meaning": "Suspiciously constant readings", "handling": "Review sensor behavior and affected time interval."},
        {"flag": "SPIKE", "meaning": "Rapid isolated transient change", "handling": "Diagnostic by default; do not discard real plume."},
        {"flag": "RESTART / STARTUP", "meaning": "Device restart or warmup period", "handling": "Preserve provenance and gate analysis as configured."},
        {"flag": "SENSOR_FAULT", "meaning": "Sensor hardware diagnostic error", "handling": "Expose fault and suppress unsupported interpretations."},
        {"flag": "HUMIDITY", "meaning": "High humidity reliability risk", "handling": "Show context; do not claim correction unless validated."},
        {"flag": "CLOCK_UNSYNCED", "meaning": "Timestamp unaligned with NTP", "handling": "Do not invent wall-clock time."},
        {"flag": "SOURCE_REVIEW", "meaning": "Malformed or corrupted record", "handling": "Retain raw source and mark for operator review."},
        {"flag": "GAP", "meaning": "Missing interval in time-series", "handling": "Represent gap explicitly rather than interpolating."}
    ]

    return {
        "metrics": {
            "sample_records": 5910,
            "timestamped_records": 5838,
            "minute_bins": 99,
            "pm_eligible_samples": 5850,
            "excluded_samples": 60,
            "coverage_fraction": 0.808
        },
        "channels": {
            "pm": {"status": "Available", "channels": ["PM1", "PM2.5", "PM4", "PM10"], "color": "green"},
            "particle_counts": {"status": "Semantics unverified", "channels": ["nc0.5", "nc1.0", "nc2.5", "nc4", "nc10"], "color": "amber"},
            "gas_indices": {"status": "Not gas-ready", "channels": ["VOC Index", "NOx Index"], "color": "amber"},
            "weather": {"status": "Available", "channels": ["Temperature", "Humidity", "Pressure"], "color": "green"},
            "baseline_maturity": {"status": "Known timing issue", "channels": ["Exponential baseline"], "color": "amber"}
        },
        "manifest": manifest_data,
        "flags": flags
    }


class InterventionCreate(BaseModel):
    title: str
    owner: str
    status: str
    start: Optional[str] = None
    end: Optional[str] = None
    rationale: str

@router.get("/interventions")
def get_interventions():
    """Returns registered interventions and proposed trials."""
    return {"interventions": _interventions}

@router.post("/interventions")
def create_intervention(intv: InterventionCreate):
    """Creates a new intervention record."""
    new_id = f"INT-{len(_interventions) + 1:03d}"
    item = {
        "id": new_id,
        "title": intv.title,
        "owner": intv.owner,
        "status": intv.status,
        "start": intv.start or "",
        "end": intv.end or "",
        "rationale": intv.rationale,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    _interventions.insert(0, item)
    return {"status": "CREATED", "intervention": item, "interventions": _interventions}


class ObservationCreate(BaseModel):
    time: str
    type: str
    count: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None

@router.get("/observations")
def get_observations():
    """Returns registered activity observations."""
    return {"observations": _observations}

@router.post("/observations")
def create_observation(obs: ObservationCreate):
    """Creates a new ground-truth activity observation record."""
    new_id = f"OBS-{len(_observations) + 1:03d}"
    item = {
        "id": new_id,
        "time": obs.time,
        "type": obs.type,
        "count": obs.count or "",
        "source": obs.source or "Field observer",
        "notes": obs.notes or "",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    _observations.insert(0, item)
    return {"status": "CREATED", "observation": item, "observations": _observations}


@router.get("/report/daily")
def get_daily_report():
    """Returns the pre-computed daily report from reporting pipeline."""
    report_data = _read_json_file("reports/ft1_final_v2/daily/report.json")
    if not report_data:
        raise HTTPException(status_code=404, detail="Daily report not found")
    return report_data
