from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class WarningConfig:
    """Prototype triage thresholds, not official AQI or medical thresholds."""
    watch_excess_ug_m3: float = 15.0
    elevated_excess_ug_m3: float = 30.0
    severe_excess_ug_m3: float = 75.0
    elevated_duration_min: float = 3.0
    minimum_event_coverage: float = 0.70
    low_coverage_cutoff: float = 0.70
    version: str = "0.1.0"

    def as_dict(self):
        return asdict(self)