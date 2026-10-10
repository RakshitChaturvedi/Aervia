from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import hashlib, json
from .config import AdvisoryConfig
from .context_builder import build_context
from .rules import select_recommendations
from .schemas import AdvisoryAction, AdvisoryRecord
from .llm_generator import generate_with_gemini
from .validator import validate_llm_output

@dataclass
class AdvisoryEngine:
    config: AdvisoryConfig

    def generate(self, warning: dict[str, Any], analytics_dir=None, features_path=None) -> dict[str, Any]:
        context = build_context(warning, analytics_dir, features_path)
        rules = select_recommendations(context, self.config.language, self.config.max_actions)
        summary, reasoning = self._fallback_text(warning, rules)
        actions = rules["actions"]
        mode = "DETERMINISTIC"
        if self.config.llm_enabled and self.config.gemini_api_key:
            try:
                llm = generate_with_gemini(self.config.gemini_api_key, self.config.gemini_model, self.config.language, context, rules)
                validated = validate_llm_output(llm, actions)
                summary, reasoning = validated["summary"], validated["reasoning"]
                for action in actions:
                    words = validated["actions"][action["action_id"]]
                    action.update(words)
                mode = "GEMINI"
            except Exception as exc:
                # Deterministic recommendations remain usable if the provider fails or output is invalid.
                mode = "DETERMINISTIC_FALLBACK"
                llm_error = f"LLM generation/validation failed: {type(exc).__name__}"
            else:
                llm_error = None
        else:
            llm_error = None
        warning_id = str(warning.get("warning_id", "unknown-warning"))
        event_id = str(warning.get("event_id", "unknown-event"))
        record = AdvisoryRecord(
            advisory_id=f"{warning_id}:advisory", warning_id=warning_id, event_id=event_id,
            status="GENERATED", language=self.config.language, summary=summary, reasoning=reasoning,
            actions=[AdvisoryAction(**a) for a in actions], evidence=rules["evidence"],
            uncertainty=rules["uncertainty"], limitations=list(warning.get("limitations") or []) + ["Recommendations are rule-based prototype guidance, not medical advice."],
            generation_mode=mode, generated_at_utc=datetime.now(timezone.utc).isoformat(),
        ).to_dict()
        if llm_error:
            record["generation_note"] = llm_error
        record["input_fingerprint"] = hashlib.sha256(json.dumps(warning, sort_keys=True, default=str).encode()).hexdigest()
        return record

    @staticmethod
    def _fallback_text(warning: dict[str, Any], rules: dict[str, Any]) -> tuple[str, str]:
        severity = str(warning.get("severity", "unknown")).lower()
        pollutant = str(warning.get("pollutant", "pollutant"))
        peak = warning.get("peak_pm2_5_ug_m3")
        excess = warning.get("peak_excess_pm2_5_ug_m3")
        if peak is not None and excess is not None:
            summary = f"A {severity} {pollutant} event was recorded, with peak PM2.5 of {float(peak):.1f} µg/m³ and peak excess over the estimated baseline of {float(excess):.1f} µg/m³."
        else:
            summary = f"A {severity} {pollutant} warning was recorded. Review the supporting evidence and data-quality limitations."
        reasoning = "Recommendations were selected using configured rules and the available warning evidence. " + " ".join(rules["uncertainty"][:2])
        if str(warning.get("lifecycle", "")).upper() == "OPEN_AT_CAPTURE_END":
            reasoning += " The recording ended during the event, so its current state is unknown."
        return summary, reasoning