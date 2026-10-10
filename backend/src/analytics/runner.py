from pathlib import Path
import pandas as pd
from .config import AnalyticsConfig
from .schemas import write_json, AnalysisStatus
from .event_detection import detect_events
from .recovery_profile import profile_recovery
from .exposure_burden import calculate_exposure_burden
from .activity_association import analyze_activity_association
from .intervention_check import check_interventions

def run_analytics(features_path, output_dir, activities_path=None, interventions_path=None, config=None):
    cfg=config or AnalyticsConfig()
    features_path=Path(features_path); output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    features=pd.read_csv(features_path)
    if features.empty: raise ValueError("features.csv is empty.")
    dataset_id=cfg.dataset_id if cfg.dataset_id!="unspecified" else features_path.stem
    activities=pd.read_csv(activities_path) if activities_path else None
    interventions=pd.read_csv(interventions_path) if interventions_path else None
    event=detect_events(features,cfg.event,dataset_id)
    events=event.results if event.status not in {AnalysisStatus.FAILED_VALIDATION,AnalysisStatus.INSUFFICIENT_DATA} else []
    results=[event,profile_recovery(features,events,cfg.recovery,dataset_id),
      calculate_exposure_burden(features,events or None,cfg.exposure,dataset_id),
      analyze_activity_association(features,activities,cfg.activity,dataset_id),
      check_interventions(features,interventions,cfg.intervention,dataset_id)]
    for result in results:
        write_json(output_dir/f"{result.module}.json",result.to_dict())
        pd.DataFrame(result.results).to_csv(output_dir/f"{result.module}.csv",index=False)
    manifest={"layer":"3B","algorithm_version":"0.2.0","dataset_id":dataset_id,
      "input_features_path":str(features_path),"input_rows":len(features),"config":cfg.to_dict(),
      "context_inputs":{"activities_path":str(activities_path) if activities_path else None,
                        "interventions_path":str(interventions_path) if interventions_path else None},
      "module_statuses":{r.module:r.status.value for r in results},
      "output_counts":{r.module:len(r.results) for r in results},
      "limitations":["Thresholds are provisional exploratory defaults.",
        "Known Layer 3A baseline-maturity timing discrepancy remains.",
        "Activity and intervention analyses require synchronized context.",
        "No source attribution, personal dose, population exposure, or causal effect is inferred."]}
    write_json(output_dir/"manifest.json",manifest)
    return manifest