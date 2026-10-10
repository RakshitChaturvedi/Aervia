import pandas as pd
from .schemas import AnalysisStatus
from .common import normalize_features, eligible_mask, make_result
from .config import InterventionConfig

def check_interventions(features, interventions=None, config=None, dataset_id="unspecified"):
    cfg=config or InterventionConfig()
    df,error=normalize_features(features,{"timestamp","pm2_5","analysis_ok"})
    if error:
        return make_result("intervention_check",AnalysisStatus.FAILED_VALIDATION,pd.DataFrame(columns=["timestamp"]),dataset_id,cfg.__dict__,[],{},[error],exclusions=[error])
    if interventions is None or interventions.empty:
        return make_result("intervention_check",AnalysisStatus.NOT_RUN,df,dataset_id,cfg.__dict__,[],{"pm2_5":"µg/m³"},
                           ["No intervention record supplied; no intervention is assumed."])
    required={"intervention_id","intervention","start_utc","end_utc"}
    if not required.issubset(interventions.columns):
        return make_result("intervention_check",AnalysisStatus.FAILED_VALIDATION,df,dataset_id,cfg.__dict__,[],{},[f"Missing intervention columns: {sorted(required-set(interventions.columns))}"])
    if min(cfg.pre_window_minutes,cfg.post_window_minutes,cfg.minimum_eligible_minutes_per_window)<1:
        return make_result("intervention_check",AnalysisStatus.FAILED_VALIDATION,df,dataset_id,cfg.__dict__,[],{},["Invalid intervention configuration."])
    ctx=interventions.copy(); ctx["start_utc"]=pd.to_datetime(ctx.start_utc,utc=True,errors="coerce"); ctx["end_utc"]=pd.to_datetime(ctx.end_utc,utc=True,errors="coerce")
    if ctx[["start_utc","end_utc"]].isna().any().any() or (ctx.end_utc<ctx.start_utc).any():
        return make_result("intervention_check",AnalysisStatus.FAILED_VALIDATION,df,dataset_id,cfg.__dict__,[],{},["Invalid intervention timestamps."])
    df["pm2_5"]=pd.to_numeric(df.pm2_5,errors="coerce"); eligible=eligible_mask(df,"pm2_5"); rows=[]
    for _,it in ctx.iterrows():
        start,end=it.start_utc,it.end_utc
        pre=df[(df.timestamp>=start-pd.Timedelta(minutes=cfg.pre_window_minutes))&(df.timestamp<start)]
        post=df[(df.timestamp>end)&(df.timestamp<=end+pd.Timedelta(minutes=cfg.post_window_minutes))]
        pre=pre.loc[eligible.loc[pre.index]]; post=post.loc[eligible.loc[post.index]]
        pc=min(1.,len(pre)/cfg.pre_window_minutes); qc=min(1.,len(post)/cfg.post_window_minutes)
        adequate=(len(pre)>=cfg.minimum_eligible_minutes_per_window and len(post)>=cfg.minimum_eligible_minutes_per_window and pc>=cfg.minimum_coverage_fraction and qc>=cfg.minimum_coverage_fraction)
        pm=float(pre.pm2_5.mean()) if len(pre) else None; qm=float(post.pm2_5.mean()) if len(post) else None
        diff=qm-pm if adequate else None
        rows.append({"intervention_id":str(it.intervention_id),"intervention":str(it.intervention),
          "start_utc":start.isoformat(),"end_utc":end.isoformat(),"pre_window_minutes":cfg.pre_window_minutes,
          "post_window_minutes":cfg.post_window_minutes,"pre_eligible_minutes":len(pre),"post_eligible_minutes":len(post),
          "pre_coverage_fraction":pc,"post_coverage_fraction":qc,"pre_mean_pm2_5_ug_m3":pm,"post_mean_pm2_5_ug_m3":qm,
          "absolute_difference_post_minus_pre_ug_m3":diff,"relative_difference_percent":diff/pm*100 if adequate and pm not in (None,0) else None,
          "status":"OBSERVED_CHANGE" if adequate else "INSUFFICIENT_DATA",
          "interpretation":"Observed before/after difference only; not a causal effect estimate."})
    status=AnalysisStatus.OK if rows and all(r["status"]=="OBSERVED_CHANGE" for r in rows) else AnalysisStatus.PARTIAL
    return make_result("intervention_check",status,df,dataset_id,cfg.__dict__,rows,{"pm2_5":"µg/m³","relative_difference":"%"},
      ["Observed change is not proof of causal impact.","Weather, traffic, background pollution, and regression to the mean may confound comparisons."],
      eligible=eligible,valid_outputs=["pre/post metrics when coverage is adequate"])