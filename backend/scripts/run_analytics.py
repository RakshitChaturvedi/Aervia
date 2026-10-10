import argparse, json
from src.analytics.runner import run_analytics
from src.analytics.config import AnalyticsConfig, EventDetectionConfig, RecoveryConfig, ExposureConfig, ActivityConfig, InterventionConfig

def main():
    p=argparse.ArgumentParser(description="Run Aervia Layer 3B.")
    p.add_argument("--features",required=True); p.add_argument("--output",required=True)
    p.add_argument("--dataset-id",default="unspecified"); p.add_argument("--activities"); p.add_argument("--interventions")
    p.add_argument("--event-excess-threshold",type=float,default=15.0)
    p.add_argument("--event-persistence-minutes",type=int,default=2); p.add_argument("--event-gap-tolerance-minutes",type=int,default=1)
    p.add_argument("--recovery-threshold",type=float,default=5.0); p.add_argument("--recovery-window-minutes",type=int,default=60)
    p.add_argument("--max-integration-gap-minutes",type=float,default=2.0)
    args=p.parse_args()
    cfg=AnalyticsConfig(dataset_id=args.dataset_id,
      event=EventDetectionConfig(excess_threshold_ug_m3=args.event_excess_threshold,persistence_minutes=args.event_persistence_minutes,
        gap_tolerance_minutes=args.event_gap_tolerance_minutes),
      recovery=RecoveryConfig(recovery_excess_threshold_ug_m3=args.recovery_threshold,observation_window_minutes=args.recovery_window_minutes),
      exposure=ExposureConfig(maximum_integration_gap_minutes=args.max_integration_gap_minutes))
    print(json.dumps(run_analytics(args.features,args.output,args.activities,args.interventions,cfg),indent=2))
if __name__=="__main__": main()