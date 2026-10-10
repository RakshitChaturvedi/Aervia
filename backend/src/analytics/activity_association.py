import pandas as pd
from .schemas import AnalysisStatus
from .common import normalize_features, eligible_mask, make_result
from .config import ActivityConfig

def analyze_activity_association(features, activities=None, config=None, dataset_id="unspecified"):
    cfg=config or ActivityConfig()
    df,error=normalize_features(features,{"timestamp","pm2_5","analysis_ok"})
    if error:
        return make_result("activity_association",AnalysisStatus.FAILED_VALIDATION,pd.DataFrame(columns=["timestamp"]),dataset_id,cfg.__dict__,[],{},[error],exclusions=[error])
    if activities is None or activities.empty:
        return make_result("activity_association",AnalysisStatus.INSUFFICIENT_CONTEXT_DATA,df,dataset_id,cfg.__dict__,[],{"pm2_5":"µg/m³"},
                           ["No synchronized activity/context data supplied; no association was calculated."])
    required={"activity","start_utc","end_utc"}
    if not required.issubset(activities.columns):
        return make_result("activity_association",AnalysisStatus.FAILED_VALIDATION,df,dataset_id,cfg.__dict__,[],{},[f"Missing activity columns: {sorted(required-set(activities.columns))}"])
    ctx=activities.copy(); ctx["start_utc"]=pd.to_datetime(ctx.start_utc,utc=True,errors="coerce"); ctx["end_utc"]=pd.to_datetime(ctx.end_utc,utc=True,errors="coerce")
    if ctx[["start_utc","end_utc"]].isna().any().any() or (ctx.end_utc<ctx.start_utc).any():
        return make_result("activity_association",AnalysisStatus.FAILED_VALIDATION,df,dataset_id,cfg.__dict__,[],{},["Invalid activity interval timestamps."])
    df["pm2_5"]=pd.to_numeric(df.pm2_5,errors="coerce"); eligible=eligible_mask(df,"pm2_5"); rows=[]
    for _,a in ctx.iterrows():
        mask=(df.timestamp>=a.start_utc)&(df.timestamp<=a.end_utc)&eligible; vals=df.loc[mask,"pm2_5"]
        expected=max(1,int(round((a.end_utc-a.start_utc).total_seconds()/60))+1); cov=min(1.,len(vals)/expected)
        rows.append({"activity":str(a.activity),"start_utc":a.start_utc.isoformat(),"end_utc":a.end_utc.isoformat(),
          "eligible_sample_count":len(vals),"mean_pm2_5_ug_m3":float(vals.mean()) if len(vals) else None,
          "median_pm2_5_ug_m3":float(vals.median()) if len(vals) else None,"maximum_pm2_5_ug_m3":float(vals.max()) if len(vals) else None,
          "coverage_fraction":cov,"status":"OK" if len(vals)>=cfg.minimum_samples_per_group and cov>=cfg.minimum_coverage_fraction else "INSUFFICIENT_DATA"})
    status=AnalysisStatus.OK if rows and all(r["status"]=="OK" for r in rows) else AnalysisStatus.PARTIAL
    return make_result("activity_association",status,df,dataset_id,cfg.__dict__,rows,{"pm2_5":"µg/m³"},
      ["Period summaries are descriptive, not causal.",
       "A comparison-period definition is required before making comparative claims.",
       "Potential confounders and context coverage must be reviewed."],eligible=eligible,
      valid_outputs=["activity-period descriptive statistics"])