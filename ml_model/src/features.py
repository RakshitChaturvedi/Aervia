"""
Physics-based feature engineering for VayuBudhi atmospheric models.
Includes Ventilation Index, boundary layer interactions, etc.
"""

def calculate_ventilation_index(pblh: float, wind_speed: float) -> float:
    """
    Calculates Ventilation Index (PBLH * Wind Speed).
    
    Args:
        pblh: Planetary Boundary Layer Height (m)
        wind_speed: Wind speed at 10m (m/s)
        
    Returns:
        Ventilation Index (m^2/s)
    """
    return max(0.0, float(pblh * wind_speed))

