import numpy as np
import pandas as pd
from src.analytics.config import EventDetectionConfig, RecoveryConfig, ExposureConfig
from src.analytics.event_detection import detect_events
from src.analytics.recovery_profile import profile_recovery
from src.analytics.exposure_burden import calculate_exposure_burden
from src.analytics.activity_association import analyze_activity_association
from src.analytics.intervention_check import check_interventions

def frame(pm, baseline=None, analysis_ok=None):
    n=len(pm); baseline=baseline if baseline is not None else [20.]*n
    return pd.DataFrame({"timestamp":pd.date_range("2026-01-01T00:00:00Z",periods=n,freq="min"),
      "pm2_5":pm,"baseline_pm2_5":baseline,"pm2_5_excess":[c-b for c,b in zip(pm,baseline)],
      "analysis_ok":analysis_ok if analysis_ok is not None else [True]*n})

def test_sustained_event_detected():
    r=detect_events(frame([20,21,40,42,41,22]),EventDetectionConfig(excess_threshold_ug_m3=15,persistence_minutes=2))
    assert len(r.results)==1 and r.results[0]["peak_excess_pm2_5_ug_m3"]==22

def test_single_spike_not_persistent():
    r=detect_events(frame([20,21,60,22]),EventDetectionConfig(excess_threshold_ug_m3=15,persistence_minutes=2))
    assert not r.results

def test_missing_baseline_not_used_for_event():
    r=detect_events(frame([20,40,42,20],[20,np.nan,20,20]),EventDetectionConfig(excess_threshold_ug_m3=15,persistence_minutes=1))
    assert all(not e["start_utc"].startswith("2026-01-01T00:01") for e in r.results)

def test_exposure_integral_constant_concentration():
    r=calculate_exposure_burden(frame([30,30,30],[20,20,20]),config=ExposureConfig())
    x=r.results[0]
    assert x["total_concentration_time_integral_ug_min_m3"]==60
    assert x["positive_excess_time_integral_ug_min_m3"]==20
    assert x["positive_excess_time_integral_ug_h_m3"]==20/60

def test_exposure_rejects_long_gap():
    df=frame([30,30,30]); df.loc[2,"timestamp"]+=pd.Timedelta(minutes=5)
    r=calculate_exposure_burden(df,config=ExposureConfig(maximum_integration_gap_minutes=2))
    assert r.results[0]["rejected_gap_segments"]>=1

def test_recovery_fit_not_justified_with_few_rows():
    df=frame([60,55,50,45,40])
    ev=[{"event_id":"e1","peak_utc":df.timestamp.iloc[0].isoformat(),"end_utc":df.timestamp.iloc[0].isoformat(),"peak_excess_pm2_5_ug_m3":40}]
    r=profile_recovery(df,ev,RecoveryConfig(minimum_fit_observations=8))
    assert r.results[0]["decay_fit"]["status"]=="FIT_NOT_JUSTIFIED"

def test_activity_without_context():
    assert analyze_activity_association(frame([20,21]),None).status.value=="INSUFFICIENT_CONTEXT_DATA"

def test_intervention_without_record():
    assert check_interventions(frame([20,21]),None).status.value=="NOT_RUN"