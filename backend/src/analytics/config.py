from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class EventDetectionConfig:
    excess_threshold_ug_m3: float = 15.0
    concentration_threshold_ug_m3: float | None = None
    persistence_minutes: int = 2
    gap_tolerance_minutes: int = 1
    minimum_coverage_fraction: float = 0.70
    minimum_eligible_minutes: int = 2

@dataclass(frozen=True)
class RecoveryConfig:
    recovery_excess_threshold_ug_m3: float = 5.0
    consecutive_minutes: int = 3
    observation_window_minutes: int = 60
    minimum_fit_observations: int = 8
    minimum_fit_r_squared: float = 0.70
    minimum_fit_dynamic_range_ug_m3: float = 2.0

@dataclass(frozen=True)
class ExposureConfig:
    maximum_integration_gap_minutes: float = 2.0
    minimum_coverage_fraction: float = 0.70

@dataclass(frozen=True)
class ActivityConfig:
    minimum_coverage_fraction: float = 0.70
    minimum_samples_per_group: int = 3

@dataclass(frozen=True)
class InterventionConfig:
    pre_window_minutes: int = 10
    post_window_minutes: int = 10
    minimum_eligible_minutes_per_window: int = 5
    minimum_coverage_fraction: float = 0.70

@dataclass(frozen=True)
class AnalyticsConfig:
    dataset_id: str = "unspecified"
    event: EventDetectionConfig = EventDetectionConfig()
    recovery: RecoveryConfig = RecoveryConfig()
    exposure: ExposureConfig = ExposureConfig()
    activity: ActivityConfig = ActivityConfig()
    intervention: InterventionConfig = InterventionConfig()
    def to_dict(self): return asdict(self)