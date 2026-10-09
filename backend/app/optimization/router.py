"""
Uncertainty-routing logic dispatcher.
Chooses whether to dispatch drone or human inspector based on model prediction confidence.
"""
from typing import Dict, Any

def dispatch_decision(attribution_confidence: float, threshold: float = 0.85) -> str:
    """
    Decides the mode of inspection.
    
    Args:
        attribution_confidence: confidence score of source attribution model.
        threshold: confidence value cutoff.
        
    Returns:
        "DRONE" or "HUMAN_INSPECTOR"
    """
    if attribution_confidence < threshold:
        return "HUMAN_INSPECTOR"  # Dispatch inspector for verification
    return "DRONE"  # Dispatch automated drone for confirmation

def get_dispatch_details(severity: float, set_size: int, threshold: float = 200.0) -> dict:
    """
    Implements uncertainty-aware dispatch logic.
    
    Returns a dict with:
        "action": str ("FULL_INSPECTION", "VERIFY_FIRST", or "MONITOR")
        "vehicle_type": str ("inspector", "van", "drone", or "none")
        "vehicle_index": int (0 for inspector, 1 for van, 2 for drone, -1 for none)
    """
    if severity < threshold:
        return {
            "action": "MONITOR",
            "vehicle_type": "none",
            "vehicle_index": -1
        }
    
    scale = threshold / 200.0
    if set_size == 1:
        if severity >= (300.0 * scale):
            return {
                "action": "FULL_INSPECTION",
                "vehicle_type": "inspector",
                "vehicle_index": 0
            }
        else:
            return {
                "action": "FULL_INSPECTION",
                "vehicle_type": "van",
                "vehicle_index": 1
            }
            
    if set_size >= 2:
        if severity >= threshold:
            return {
                "action": "VERIFY_FIRST",
                "vehicle_type": "drone",
                "vehicle_index": 2
            }
            
    return {
        "action": "MONITOR",
        "vehicle_type": "none",
        "vehicle_index": -1
    }
