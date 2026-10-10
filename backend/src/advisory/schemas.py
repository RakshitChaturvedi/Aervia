from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class AdvisoryAction:
    action_id: str
    title: str
    instruction: str
    rationale: str
    urgency: str = "ROUTINE"
    audience: str = "SITE_OPERATOR"
    evidence_refs: list[str] = field(default_factory=list)

@dataclass
class AdvisoryRecord:
    advisory_id: str
    warning_id: str
    event_id: str
    status: str
    language: str
    summary: str
    reasoning: str
    actions: list[AdvisoryAction]
    evidence: list[dict[str, Any]]
    uncertainty: list[str]
    limitations: list[str]
    generation_mode: str
    generated_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)