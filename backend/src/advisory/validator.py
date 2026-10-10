from __future__ import annotations
from typing import Any

REQUIRED_TOP_LEVEL = {"summary", "reasoning", "action_wording", "language"}

def validate_llm_output(output: dict[str, Any], approved_actions: list[dict[str, Any]]) -> dict[str, Any]:
    if not REQUIRED_TOP_LEVEL.issubset(output):
        raise ValueError("LLM output is missing required fields")
    if not isinstance(output["summary"], str) or not output["summary"].strip():
        raise ValueError("LLM summary must be a non-empty string")
    if not isinstance(output["reasoning"], str) or not output["reasoning"].strip():
        raise ValueError("LLM reasoning must be a non-empty string")
    if not isinstance(output["action_wording"], list):
        raise ValueError("LLM action_wording must be a list")
    approved = {a["action_id"]: a for a in approved_actions}
    seen = set()
    result = {}
    for item in output["action_wording"]:
        if not isinstance(item, dict) or item.get("action_id") not in approved:
            raise ValueError("LLM referenced an unapproved action")
        action_id = item["action_id"]
        if action_id in seen:
            raise ValueError("LLM returned a duplicate action")
        seen.add(action_id)
        original = approved[action_id]
        # Keep deterministic rationale and metadata; only accept generated wording fields.
        result[action_id] = {
            "title": _safe_text(item.get("title"), original["title"]),
            "instruction": _safe_text(item.get("instruction"), original["instruction"]),
            "rationale": _safe_text(item.get("rationale"), original["rationale"]),
        }
    if seen != set(approved):
        raise ValueError("LLM omitted one or more approved actions")
    return {"summary": output["summary"].strip(), "reasoning": output["reasoning"].strip(), "actions": result, "language": str(output.get("language", "en"))}

def _safe_text(value: Any, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1200:
        return fallback
    return value.strip()