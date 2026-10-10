import pandas as pd
from .schemas import AnalysisStatus
from .common import normalize_features, eligible_mask, make_result
from .config import ExposureConfig

def _integrate(w, eligibility, max_gap):
    total=excess=baseline=duration=0.0; valid=reject=0
    if len(w)<2:
        return dict(total=None,excess=None,baseline=None,duration=0.,valid=0,rejected=0)
    x=w.copy(); x["_eligible"]=eligibility.to_numpy(); x=x.sort_values("timestamp").reset_index(drop=True)
    for i in range(len(x)-1):
        a,b=x.iloc[i],x.iloc[i+1]; dt=(b.timestamp-a.timestamp).total_seconds()/60
        if dt<=0: continue
        if not a["_eligible"] or not b["_eligible"] or dt>max_gap:
            reject+=1; continue
        c0,c1=float(a.pm2_5),float(b.pm2_5); b0,b1=float(a.baseline_pm2_5),float(b.baseline_pm2_5)
        e0,e1=max(c0-b0,0),max(c1-b1,0)
        total+=(c0+c1)*.5*dt; baseline+=(b0+b1)*.5*dt; excess+=(e0+e1)*.5*dt
        duration+=dt; valid+=1
    return dict(total=total if valid else None,excess=excess if valid else None,baseline=baseline if valid else None,
                duration=duration,valid=valid,rejected=reject)

def calculate_exposure_burden(features, events=None, config=None, dataset_id="unspecified"):
    cfg=config or ExposureConfig()
    df,error=normalize_features(features,{"timestamp","pm2_5","baseline_pm2_5","pm2_5_excess","analysis_ok"})
    if error:
        return make_result("exposure_burden",AnalysisStatus.FAILED_VALIDATION,pd.DataFrame(columns=["timestamp"]),dataset_id,cfg.__dict__,[],{},[error],exclusions=[error])
    if cfg.maximum_integration_gap_minutes<=0 or not 0<=cfg.minimum_coverage_fraction<=1:
        return make_result("exposure_burden",AnalysisStatus.FAILED_VALIDATION,df,dataset_id,cfg.__dict__,[],{},["Invalid exposure configuration."])
    for c in ("pm2_5","baseline_pm2_5","pm2_5_excess"): df[c]=pd.to_numeric(df[c],errors="coerce")
    eligible=eligible_mask(df,"pm2_5")&df.baseline_pm2_5.notna()&df.pm2_5_excess.notna()
    windows=[(e["event_id"],pd.to_datetime(e["start_utc"],utc=True),pd.to_datetime(e["end_utc"],utc=True)) for e in events] if events else [
        ("period:full_observation",df.timestamp.min(),df.timestamp.max())]
    rows=[]; partial=False
    for wid,start,end in windows:
        w=df[(df.timestamp>=start)&(df.timestamp<=end)].copy(); integ=_integrate(w,eligible.loc[w.index],cfg.maximum_integration_gap_minutes)
        expected=(end-start).total_seconds()/60
        coverage=min(1.,integ["duration"]/expected) if expected>0 else (1. if len(w) else 0.)
        adequate=coverage>=cfg.minimum_coverage_fraction
        partial |= not adequate
        rows.append({"window_id":wid,"start_utc":start.isoformat(),"end_utc":end.isoformat(),"pollutant":"PM2.5",
          "concentration_unit":"µg/m³","total_concentration_time_integral_ug_min_m3":integ["total"],
          "positive_excess_time_integral_ug_min_m3":integ["excess"],
          "positive_excess_time_integral_ug_h_m3":integ["excess"]/60 if integ["excess"] is not None else None,
          "baseline_time_integral_ug_min_m3":integ["baseline"],"integrated_duration_min":integ["duration"],
          "expected_duration_min":expected,"coverage_fraction":coverage,"valid_segments":integ["valid"],
          "rejected_gap_segments":integ["rejected"],"status":"OK" if adequate else "PARTIAL"})
    return make_result("exposure_burden",AnalysisStatus.PARTIAL if partial else AnalysisStatus.OK,df,dataset_id,cfg.__dict__,rows,
      {"concentration":"µg/m³","integral_min":"µg·min/m³","integral_hour":"µg·h/m³","duration":"min"},
      ["Trapezoidal integration over adjacent eligible observations only.",
       "Intervals exceeding the maximum gap are excluded, not interpolated.",
       "Positive excess is max(PM2.5 - baseline, 0); PM fractions are not summed.",
       "This is concentration-time, not personal dose or population exposure."],eligible=eligible,
      exclusions=[f"ineligible_rows={int((~eligible).sum())}"],valid_outputs=["total concentration-time","positive excess integral","baseline integral","coverage"])