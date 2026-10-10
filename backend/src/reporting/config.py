from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ReportConfig:
    dataset_id: str
    report_type: str = "daily"       # event, hourly, daily, weekly, custom
    start_utc: Optional[str] = None
    end_utc: Optional[str] = None
    audience: str = "operator"       # operator, admin, technical
    include_advisories: bool = True
    include_environmental_context: bool = True
    include_data_quality: bool = True

    def validate(self) -> None:
        if self.report_type not in {"event", "hourly", "daily", "weekly", "custom"}:
            raise ValueError(f"Unsupported report_type: {self.report_type}")
        if self.audience not in {"operator", "admin", "technical"}:
            raise ValueError(f"Unsupported audience: {self.audience}")
        if self.report_type == "custom" and (not self.start_utc or not self.end_utc):
            raise ValueError("custom reports require --start-utc and --end-utc")