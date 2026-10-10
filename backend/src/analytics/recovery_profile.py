import math
import numpy as np
import pandas as pd
from .schemas import AnalysisStatus
from .common import normalize_features, eligible_mask, make_result
from .config import RecoveryConfig

def _fit_decay(post, peak_time, peak_excess, cfg):
    out = {"status":"FIT_NOT_JUSTIFIED", "decay_rate_per_min":None, "half_life_min":None,
           "r_squared":None, "n_observations":0, "standard_error_log_slope":None, "diagnostic":None}
    if post.empty or not np.isfinite(peak_excess) or peak_excess <= 0:
        out["diagnostic"]="No valid post-peak observations or non-positive peak excess."; return out
    y = pd.to_numeric(post.pm2_5_excess, errors="coerce").to_numpy(float)
    t = (post.timestamp-peak_time).dt.total_seconds().to_numpy(float)/60
    valid = np.isfinite(y) & (y>0) & np.isfinite(t)
    y,t=y[valid],t[valid]; out["n_observations"]=int(len(y))
    if len(y)<cfg.minimum_fit_observations:
        out["diagnostic"]="Insufficient positive observations."; return out
    if y.max()-y.min()<cfg.minimum_fit_dynamic_range_ug_m3:
        out["diagnostic"]="Insufficient dynamic range."; return out
    slope, intercept=np.polyfit(t,np.log(y),1); residual=np.log(y)-(intercept+slope*t)
    ssr=float(np.sum(residual**2)); sst=float(np.sum((np.log(y)-np.mean(np.log(y)))**2))
    r2=1-ssr/sst if sst>0 else None; dof=len(y)-2
    denom=float(np.sum((t-np.mean(t))**2))
    se=math.sqrt(ssr/dof/denom) if dof>0 and denom>0 else None
    out.update(r_squared=r2,standard_error_log_slope=se)
    if slope>=0: out["diagnostic"]="Fitted slope is not decaying."; return out
    if r2 is None or r2<cfg.minimum_fit_r_squared:
        out["diagnostic"]="Fit R-squared below configured minimum."; return out
    rate=float(-slope)
    out.update(status="FIT_OK",decay_rate_per_min=rate,half_life_min=float(math.log(2)/rate),
               diagnostic="Log-linear exponential-decay fit passed configured diagnostics.")
    return out

def profile_recovery(features, events, config=None, dataset_id="unspecified"):
    cfg=config or RecoveryConfig()
    df,error=normalize_features(features,{"timestamp","pm2_5","pm2_5_excess","analysis_ok"})
    if error:
        return make_result("recovery_profile",AnalysisStatus.FAILED_VALIDATION,pd.DataFrame(columns=["timestamp"]),
                           dataset_id,cfg.__dict__,[],{},[error],exclusions=[error])
    if cfg.consecutive_minutes<1 or cfg.observation_window_minutes<1 or cfg.minimum_fit_observations<3:
        return make_result("recovery_profile",AnalysisStatus.FAILED_VALIDATION,df,dataset_id,cfg.__dict__,[],{},["Invalid recovery configuration."])
    if not events:
        return make_result("recovery_profile",AnalysisStatus.INSUFFICIENT_DATA,df,dataset_id,cfg.__dict__,[],
                           {"recovery_time":"min","decay_rate":"min⁻¹","half_life":"min"},["No event records supplied."])
    eligible=eligible_mask(df,"pm2_5_excess"); rows=[]
    for event in events:
        peak_time=pd.to_datetime(event.get("peak_utc",event["end_utc"]),utc=True)
        end_time=pd.to_datetime(event["end_utc"],utc=True)
        stop=peak_time+pd.Timedelta(minutes=cfg.observation_window_minutes)
        post=df[(df.timestamp>peak_time)&(df.timestamp<=stop)].copy()
        post_eligible=post.loc[eligible.loc[post.index]&post.pm2_5_excess.notna()]
        recovered=None; run=0; previous=None
        for idx,row in post.iterrows():
            contiguous=previous is None or (row.timestamp-previous).total_seconds()==60
            if not contiguous: run=0
            good=bool(eligible.loc[idx]) and pd.notna(row.pm2_5_excess) and float(row.pm2_5_excess)<=cfg.recovery_excess_threshold_ug_m3
            run=run+1 if good else 0; previous=row.timestamp
            if run>=cfg.consecutive_minutes:
                recovered=row.timestamp-pd.Timedelta(minutes=cfg.consecutive_minutes-1); break
        peak_excess=float(event.get("peak_excess_pm2_5_ug_m3",np.nan))
        fit=_fit_decay(post_eligible,peak_time,peak_excess,cfg)
        complete=bool(len(post) and post.timestamp.max()>=stop)
        recovery_status="RECOVERY_OBSERVED" if recovered is not None else ("NO_RECOVERY_OBSERVED" if complete else "INCOMPLETE_FOLLOWUP")
        rows.append({"event_id":event.get("event_id"),"peak_utc":peak_time.isoformat(),
          "recovery_threshold_excess_pm2_5_ug_m3":cfg.recovery_excess_threshold_ug_m3,
          "recovery_time_from_peak_min":(recovered-peak_time).total_seconds()/60 if recovered is not None else None,
          "recovery_status":recovery_status,"post_peak_observed_rows":len(post),"post_peak_eligible_rows":len(post_eligible),
          "post_peak_coverage_fraction":min(1.,len(post_eligible)/max(1,cfg.observation_window_minutes)),"decay_fit":fit})
    statuses={r["recovery_status"] for r in rows}
    status=AnalysisStatus.OK if statuses=={"RECOVERY_OBSERVED"} else (
        AnalysisStatus.PARTIAL if "RECOVERY_OBSERVED" in statuses or any(r["decay_fit"]["status"]=="FIT_OK" for r in rows)
        or "INCOMPLETE_FOLLOWUP" in statuses else AnalysisStatus.INSUFFICIENT_DATA)
    return make_result("recovery_profile",status,df,dataset_id,cfg.__dict__,rows,
      {"recovery_time":"min","decay_rate":"min⁻¹","half_life":"min"},
      ["Recovery requires consecutive contiguous eligible minutes below threshold.",
       "Decay fits are descriptive and emitted only when diagnostics pass.",
       "Events near capture end may be right-censored."],eligible=eligible,
      valid_outputs=["observed recovery times when available","decay parameters only for FIT_OK"])