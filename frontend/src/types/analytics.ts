export interface AnalysisReadinessItem {
  status: string;
  label: string;
}

export interface AnalyticsOverview {
  location: string;
  dataset_id: string;
  capture_window: string;
  peak_pm25: number;
  events_count: number;
  warnings_count: number;
  severe_warnings: number;
  elevated_warnings: number;
  gas_ready_observations: number;
  analysis_readiness: {
    parameter_features: AnalysisReadinessItem;
    event_detection: AnalysisReadinessItem;
    recovery_profile: AnalysisReadinessItem;
    activity_association: AnalysisReadinessItem;
    intervention_check: AnalysisReadinessItem;
  };
}

export interface EventItem {
  event_id: string;
  short_id: string;
  start_utc: string;
  end_utc: string;
  start_ist?: string;
  end_ist?: string;
  start_full_ist?: string;
  end_full_ist?: string;
  duration_min: number;
  peak_utc: string;
  peak_ist?: string;
  peak_full_ist?: string;
  peak_pm25: number;
  peak_baseline: number;
  peak_excess: number;
  mean_excess: number;
  coverage_fraction: number;
  boundary_at_end: boolean;
  lifecycle: string;
  integrated_excess_ug_h_m3: number;
  recovery_status: string;
  recovery_label: string;
  warning_id?: string;
  warning_severity: string;
  warning_acknowledged: boolean;
  reasons: string[];
  limitations: string[];
  parameter_features?: {
    pm1_to_pm2_5_band?: number;
    pm2_5_to_pm4_band?: number;
    pm4_to_pm10_band?: number;
    particle_distribution_status?: string;
    particle_distribution_interpretable?: boolean;
  };
}

export interface TimelinePoint {
  timestamp: string;
  timestamp_ist?: string;
  time: string;
  pm1: number | null;
  pm2_5: number | null;
  pm4: number | null;
  pm10: number | null;
  baseline_pm2_5: number | null;
  excess_pm2_5: number | null;
  temp: number | null;
  humidity: number | null;
  voc_index: number | null;
}

export interface WarningItem {
  warning_id: string;
  short_id: string;
  event_id: string;
  short_event_id: string;
  severity: 'SEVERE' | 'ELEVATED' | string;
  status: string;
  acknowledged: boolean;
  start_utc: string;
  end_utc: string;
  start_ist?: string;
  end_ist?: string;
  peak_excess: number;
  peak_pm25: number;
  lifecycle: string;
  coverage_fraction: number;
  reasons: string[];
  limitations: string[];
  next_check: string;
}

export interface QualityData {
  metrics: {
    sample_records: number;
    timestamped_records: number;
    minute_bins: number;
    pm_eligible_samples: number;
    excluded_samples: number;
    coverage_fraction: number;
  };
  channels: Record<string, {
    status: string;
    channels: string[];
    color: string;
  }>;
  flags: Array<{
    flag: string;
    meaning: string;
    handling: string;
  }>;
  manifest?: any;
}

export interface InterventionItem {
  id: string;
  title: string;
  owner: string;
  status: string;
  start?: string;
  end?: string;
  rationale: string;
  created_at?: string;
}

export interface ObservationItem {
  id: string;
  time: string;
  type: string;
  count?: string;
  source?: string;
  notes?: string;
  created_at?: string;
}

export interface IotTelemetry {
  device_id: string;
  station_name: string;
  timestamp: string;
  timestamp_ist?: string;
  pm1: number;
  pm25: number;
  pm4: number;
  pm10: number;
  temp: number;
  humidity: number;
  pressure: number;
  voc_index: number;
  nox_index: number;
  nc0_5?: number;
  nc1_0?: number;
  nc2_5?: number;
  nc4?: number;
  nc10?: number;
  battery_v: number;
  wifi_rssi_dbm: number;
  quality_flag: string;
  status: string;
  sensor_state?: string;
  is_sensor_online?: boolean;
  source: string;
  endpoint: string;
  is_aws_connected: boolean;
  messages_received_count: number;
  last_received_utc?: string;
  last_received_ist?: string;
  aws_iot_endpoint: string;
  aws_iot_topic: string;
  last_5_records?: IotTelemetry[];
}
