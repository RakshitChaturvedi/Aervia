"""
Cost-benefit ROI calculator.
Estimates the balance between compliance enforcement costs and population exposure reduction.
"""

def calculate_inspection_roi(population_exposed: float, estimated_aqi_reduction: float, compliance_cost: float) -> float:
    """
    Computes Return on Investment (ROI) score for a route.
    
    Args:
        population_exposed: Population exposed.
        estimated_aqi_reduction: Est. reduction in AQI-exposure for local population.
        compliance_cost: Cost of running inspection route.
        
    Returns:
        ROI ratio or score
    """
    if compliance_cost <= 0:
        return 0.0
    return (population_exposed * estimated_aqi_reduction) / compliance_cost
