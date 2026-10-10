from __future__ import annotations
import json
from typing import Any


def generate_with_gemini(api_key: str, model: str, language: str, context: dict[str, Any], rules_output: dict[str, Any]) -> dict[str, Any]:
    """Generate wording only; the approved action set is not delegated to the model."""
    from google import genai
    client = genai.Client(api_key=api_key)
    warning = context.get("warning", {})
    payload = {
        "warning": {k: warning.get(k) for k in ("severity", "pollutant", "peak_pm2_5_ug_m3", "peak_baseline_pm2_5_ug_m3", "peak_excess_pm2_5_ug_m3", "duration_elapsed_minutes", "lifecycle", "current_gas_readiness")},
        "approved_actions": rules_output["actions"],
        "evidence": rules_output["evidence"],
        "uncertainty": rules_output["uncertainty"],
        "language": language,
    }
    prompt = """You are the wording component of an air-quality advisory system. Use only the supplied data. Do not add, remove, or materially change approved actions. Do not diagnose, claim a pollution source, invent measurements, make medical claims, or imply campus-wide representativeness. Preserve uncertainty and sensor-readiness limitations. Return ONLY valid JSON with keys: summary (string), reasoning (string), action_wording (array of objects with action_id, title, instruction, rationale), language (string). Translate the wording into the requested language while preserving numeric values and units. If the evidence says capture ended, do not claim current live conditions.\n\nINPUT:\n""" + json.dumps(payload, ensure_ascii=False)
    response = client.models.generate_content(model=model, contents=prompt, config={"response_mime_type": "application/json", "temperature": 0.2})
    text = getattr(response, "text", None)
    if not text:
        raise ValueError("Gemini returned an empty response")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response was not a JSON object")
    return parsed