from dataclasses import dataclass
import os

@dataclass(frozen=True)
class AdvisoryConfig:
    llm_enabled: bool = False
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    language: str = "en"
    max_actions: int = 4
    version: str = "0.1.0"

    @classmethod
    def from_env(cls) -> "AdvisoryConfig":
        enabled = os.getenv("AERVIA_ADVISORY_LLM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        return cls(
            llm_enabled=enabled,
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            language=os.getenv("AERVIA_ADVISORY_LANGUAGE", "en"),
            max_actions=max(1, min(8, int(os.getenv("AERVIA_ADVISORY_MAX_ACTIONS", "4")))),
        )