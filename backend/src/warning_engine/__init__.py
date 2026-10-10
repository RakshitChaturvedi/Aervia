"""Rule-based prototype warning engine for Aervia."""
from .engine import WarningConfig, build_warnings

__all__ = ["WarningConfig", "build_warnings"]