import {
  AnalyticsOverview,
  EventItem,
  TimelinePoint,
  WarningItem,
  QualityData,
  InterventionItem,
  ObservationItem,
  IotTelemetry,
} from '@/types/analytics';
import { apiUrl } from './api';

const API_BASE = {
  toString() {
    return apiUrl('');
  }
};

// Fallback initial data in case backend is offline
export const FALLBACK_OVERVIEW: AnalyticsOverview = {
  location: 'College Gate',
  dataset_id: 'ft1_final_v2',
  capture_window: '2026-10-09 14:24 to 16:02 IST (99 minute bins)',
  peak_pm25: 201.5,
  events_count: 4,
  warnings_count: 4,
  severe_warnings: 2,
  elevated_warnings: 2,
  gas_ready_observations: 0,
  analysis_readiness: {
    parameter_features: { status: 'OK', label: 'OK · 99 rows' },
    event_detection: { status: 'OK', label: 'OK · 4 events' },
    recovery_profile: { status: 'PARTIAL', label: 'PARTIAL · boundary limited' },
    activity_association: { status: 'CONTEXT_MISSING', label: 'Context missing' },
    intervention_check: { status: 'NOT_RUN', label: 'Not run' },
  },
};

export const FALLBACK_EVENTS: EventItem[] = [
  {
    event_id: 'ft1_final_v2:PM25:0004',
    short_id: 'E-0004',
    start_utc: '2026-10-09T10:25:00+00:00',
    end_utc: '2026-10-09T10:32:00+00:00',
    start_ist: '15:55',
    end_ist: '16:02',
    start_full_ist: '2026-10-09 15:55:00 IST',
    end_full_ist: '2026-10-09 16:02:00 IST',
    duration_min: 7.0,
    peak_utc: '2026-10-09T10:32:00+00:00',
    peak_ist: '16:02',
    peak_full_ist: '2026-10-09 16:02:00 IST',
    peak_pm25: 201.5,
    peak_baseline: 33.9,
    peak_excess: 167.6,
    mean_excess: 80.1,
    coverage_fraction: 1.0,
    boundary_at_end: true,
    lifecycle: 'OPEN_AT_CAPTURE_END',
    integrated_excess_ug_h_m3: 7.687,
    recovery_status: 'INCOMPLETE_FOLLOWUP',
    recovery_label: 'Incomplete',
    warning_id: 'ft1_final_v2:PM25:0004:warning',
    warning_severity: 'Severe',
    warning_acknowledged: false,
    reasons: [
      'peak excess crossed the prototype severe-priority threshold',
      'event persisted for at least the configured duration threshold',
      'event reaches the end of the available capture; live continuation is unknown',
    ],
    limitations: [
      'Severity is a configurable prototype triage category, not an official AQI category or medical-risk assessment.',
      'A single node does not establish conditions across the campus or identify the pollution source.',
      'A concentration-time integral is not personal inhaled dose or population exposure.',
    ],
  },
  {
    event_id: 'ft1_final_v2:PM25:0003',
    short_id: 'E-0003',
    start_utc: '2026-10-09T10:10:00+00:00',
    end_utc: '2026-10-09T10:13:00+00:00',
    start_ist: '15:40',
    end_ist: '15:43',
    start_full_ist: '2026-10-09 15:40:00 IST',
    end_full_ist: '2026-10-09 15:43:00 IST',
    duration_min: 3.0,
    peak_utc: '2026-10-09T10:10:00+00:00',
    peak_ist: '15:40',
    peak_full_ist: '2026-10-09 15:40:00 IST',
    peak_pm25: 116.9,
    peak_baseline: 26.4,
    peak_excess: 90.5,
    mean_excess: 48.4,
    coverage_fraction: 1.0,
    boundary_at_end: false,
    lifecycle: 'OBSERVED_EVENT',
    integrated_excess_ug_h_m3: 1.754,
    recovery_status: 'RECOVERY_OBSERVED',
    recovery_label: '12 min',
    warning_id: 'ft1_final_v2:PM25:0003:warning',
    warning_severity: 'Severe',
    warning_acknowledged: false,
    reasons: [
      'peak excess crossed the prototype severe-priority threshold',
      'event persisted for at least the configured duration threshold',
    ],
    limitations: [
      'Severity is a configurable prototype triage category, not an official AQI category or medical-risk assessment.',
      'A single node does not establish conditions across the campus or identify the pollution source.',
      'A concentration-time integral is not personal inhaled dose or population exposure.',
    ],
  },
  {
    event_id: 'ft1_final_v2:PM25:0002',
    short_id: 'E-0002',
    start_utc: '2026-10-09T09:36:00+00:00',
    end_utc: '2026-10-09T09:39:00+00:00',
    start_ist: '15:06',
    end_ist: '15:09',
    start_full_ist: '2026-10-09 15:06:00 IST',
    end_full_ist: '2026-10-09 15:09:00 IST',
    duration_min: 3.0,
    peak_utc: '2026-10-09T09:36:00+00:00',
    peak_ist: '15:06',
    peak_full_ist: '2026-10-09 15:06:00 IST',
    peak_pm25: 86.3,
    peak_baseline: 24.7,
    peak_excess: 61.6,
    mean_excess: 32.7,
    coverage_fraction: 1.0,
    boundary_at_end: false,
    lifecycle: 'OBSERVED_EVENT',
    integrated_excess_ug_h_m3: 1.077,
    recovery_status: 'RECOVERY_OBSERVED',
    recovery_label: '8 min',
    warning_id: 'ft1_final_v2:PM25:0002:warning',
    warning_severity: 'Elevated',
    warning_acknowledged: false,
    reasons: ['peak excess crossed the prototype elevated-priority threshold'],
    limitations: ['Provisional threshold evaluation.'],
  },
  {
    event_id: 'ft1_final_v2:PM25:0001',
    short_id: 'E-0001',
    start_utc: '2026-10-09T09:29:00+00:00',
    end_utc: '2026-10-09T09:33:00+00:00',
    start_ist: '14:59',
    end_ist: '15:03',
    start_full_ist: '2026-10-09 14:59:00 IST',
    end_full_ist: '2026-10-09 15:03:00 IST',
    duration_min: 4.0,
    peak_utc: '2026-10-09T09:29:00+00:00',
    peak_ist: '14:59',
    peak_full_ist: '2026-10-09 14:59:00 IST',
    peak_pm25: 69.9,
    peak_baseline: 24.7,
    peak_excess: 45.3,
    mean_excess: 31.6,
    coverage_fraction: 1.0,
    boundary_at_end: false,
    lifecycle: 'OBSERVED_EVENT',
    integrated_excess_ug_h_m3: 1.608,
    recovery_status: 'RECOVERY_OBSERVED',
    recovery_label: '15 min',
    warning_id: 'ft1_final_v2:PM25:0001:warning',
    warning_severity: 'Elevated',
    warning_acknowledged: false,
    reasons: ['peak excess crossed the prototype elevated-priority threshold'],
    limitations: ['Provisional threshold evaluation.'],
  },
];

export const FALLBACK_QUALITY: QualityData = {
  metrics: {
    sample_records: 5910,
    timestamped_records: 5838,
    minute_bins: 99,
    pm_eligible_samples: 5850,
    excluded_samples: 60,
    coverage_fraction: 0.808,
  },
  channels: {
    pm: { status: 'Available', channels: ['PM1', 'PM2.5', 'PM4', 'PM10'], color: 'green' },
    particle_counts: { status: 'Semantics unverified', channels: ['nc0.5', 'nc1.0', 'nc2.5', 'nc4', 'nc10'], color: 'amber' },
    gas_indices: { status: 'Not gas-ready', channels: ['VOC Index', 'NOx Index'], color: 'amber' },
    weather: { status: 'Available', channels: ['Temperature', 'Humidity', 'Pressure'], color: 'green' },
    baseline_maturity: { status: 'Known timing issue', channels: ['Exponential baseline'], color: 'amber' },
  },
  flags: [
    { flag: 'MISSING', meaning: 'Required channel absent', handling: 'Retain row; exclude from calculations requiring the value.' },
    { flag: 'OUT_OF_RANGE', meaning: 'Value outside physical bounds', handling: 'Flag and apply channel-specific eligibility rules.' },
    { flag: 'FLATLINE', meaning: 'Suspiciously constant readings', handling: 'Review sensor behavior and affected time interval.' },
    { flag: 'SPIKE', meaning: 'Rapid isolated transient change', handling: 'Diagnostic by default; do not discard real plume.' },
    { flag: 'RESTART / STARTUP', meaning: 'Device restart or warmup period', handling: 'Preserve provenance and gate analysis as configured.' },
    { flag: 'SENSOR_FAULT', meaning: 'Sensor hardware diagnostic error', handling: 'Expose fault and suppress unsupported interpretations.' },
    { flag: 'HUMIDITY', meaning: 'High humidity reliability risk', handling: 'Show context; do not claim correction unless validated.' },
    { flag: 'CLOCK_UNSYNCED', meaning: 'Timestamp unaligned with NTP', handling: 'Do not invent wall-clock time.' },
    { flag: 'SOURCE_REVIEW', meaning: 'Malformed or corrupted record', handling: 'Retain raw source and mark for operator review.' },
    { flag: 'GAP', meaning: 'Missing interval in time-series', handling: 'Represent gap explicitly rather than interpolating.' },
  ],
};

export async function fetchAnalyticsOverview(): Promise<AnalyticsOverview> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/overview`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch overview');
    return await res.json();
  } catch (e) {
    console.warn('Using fallback analytics overview:', e);
    return FALLBACK_OVERVIEW;
  }
}

export async function fetchEvents(): Promise<EventItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/events`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch events');
    const data = await res.json();
    return data.events || FALLBACK_EVENTS;
  } catch (e) {
    console.warn('Using fallback events:', e);
    return FALLBACK_EVENTS;
  }
}

export async function fetchTimeline(): Promise<TimelinePoint[]> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/timeline`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch timeline');
    const data = await res.json();
    return data.timeline || [];
  } catch (e) {
    console.warn('Failed to fetch timeline:', e);
    return [];
  }
}

export async function fetchWarnings(): Promise<WarningItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/warnings`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch warnings');
    const data = await res.json();
    return data.warnings || [];
  } catch (e) {
    console.warn('Failed to fetch warnings:', e);
    return [];
  }
}

export async function acknowledgeWarningApi(warningId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/warnings/${encodeURIComponent(warningId)}/acknowledge`, {
      method: 'POST',
    });
    return res.ok;
  } catch (e) {
    console.warn('Failed to acknowledge warning on backend:', e);
    return true; // client fallback
  }
}

export async function fetchQualityData(): Promise<QualityData> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/quality`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch quality');
    return await res.json();
  } catch (e) {
    console.warn('Using fallback quality data:', e);
    return FALLBACK_QUALITY;
  }
}

export async function fetchInterventions(): Promise<InterventionItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/interventions`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch interventions');
    const data = await res.json();
    return data.interventions || [];
  } catch (e) {
    console.warn('Using fallback interventions:', e);
    return [
      {
        id: 'INT-001',
        title: 'Engine-off protocol during bus arrival & queuing',
        owner: 'Transport & Security',
        status: 'Proposed',
        start: '2026-10-10T09:00',
        end: '2026-10-10T11:00',
        rationale: 'Linked to repeated morning excess peaks at College Gate (E-001, E-002).',
      },
    ];
  }
}

export async function createInterventionApi(item: {
  title: string;
  owner: string;
  status: string;
  start?: string;
  end?: string;
  rationale: string;
}): Promise<InterventionItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/interventions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item),
    });
    if (!res.ok) throw new Error('Failed to create intervention');
    const data = await res.json();
    return data.interventions;
  } catch (e) {
    console.warn('Failed to post intervention to backend:', e);
    throw e;
  }
}

export async function fetchObservations(): Promise<ObservationItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/observations`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch observations');
    const data = await res.json();
    return data.observations || [];
  } catch (e) {
    console.warn('Using fallback observations:', e);
    return [
      {
        id: 'OBS-001',
        time: '2026-10-09T09:28',
        type: 'Bus arrival',
        count: '2 campus shuttle buses',
        source: 'Gate supervisor',
        notes: 'Buses arrived with continuous engine idling for approx 4 minutes.',
      },
    ];
  }
}

export async function createObservationApi(obs: {
  time: string;
  type: string;
  count?: string;
  source?: string;
  notes?: string;
}): Promise<ObservationItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/observations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(obs),
    });
    if (!res.ok) throw new Error('Failed to create observation');
    const data = await res.json();
    return data.observations;
  } catch (e) {
    console.warn('Failed to post observation to backend:', e);
    throw e;
  }
}

export async function fetchDailyReport(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/report/daily`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch daily report');
    return await res.json();
  } catch (e) {
    console.warn('Failed to fetch daily report from backend:', e);
    return null;
  }
}

export async function fetchLatestIotTelemetry(): Promise<IotTelemetry | null> {
  try {
    const res = await fetch(`${API_BASE}/api/iot/latest`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch IoT telemetry');
    return await res.json();
  } catch (e) {
    console.warn('Failed to fetch IoT telemetry from backend:', e);
    return null;
  }
}

export async function fetchIotHistory(limit = 30): Promise<IotTelemetry[]> {
  try {
    const res = await fetch(`${API_BASE}/api/iot/history?limit=${limit}`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch IoT history');
    const data = await res.json();
    return data.history || [];
  } catch (e) {
    console.warn('Failed to fetch IoT history from backend:', e);
    return [];
  }
}
