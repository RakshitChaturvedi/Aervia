import math
from typing import Tuple, Dict, Any

def get_dispersion_parameters(distance_downwind_m: float, stability_class: str) -> Tuple[float, float]:
    """
    Simplified Pasquill-Gifford dispersion parameters (sigma_y, sigma_z)
    based on downwind distance (x) and atmospheric stability class.
    """
    x = max(distance_downwind_m, 1.0)
    
    # Very simplified parameterization for demonstration purposes
    if stability_class in ['A', 'B']: # Unstable
        sigma_y = 0.22 * x / math.sqrt(1 + 0.0001 * x)
        sigma_z = 0.20 * x
    elif stability_class in ['C', 'D']: # Neutral
        sigma_y = 0.08 * x / math.sqrt(1 + 0.0001 * x)
        sigma_z = 0.06 * x / math.sqrt(1 + 0.0015 * x)
    else: # E, F - Stable
        sigma_y = 0.04 * x / math.sqrt(1 + 0.0001 * x)
        sigma_z = 0.015 * x / math.sqrt(1 + 0.0003 * x)
        
    return max(sigma_y, 1.0), max(sigma_z, 1.0)

def determine_stability_class(wind_speed: float, daytime: bool = True) -> str:
    """
    Estimates Pasquill-Gifford stability class.
    """
    if wind_speed < 2.0:
        return 'A' if daytime else 'F'
    elif wind_speed < 3.0:
        return 'B' if daytime else 'E'
    elif wind_speed < 5.0:
        return 'C' if daytime else 'D'
    else:
        return 'D'

def calculate_gaussian_plume(
    x: float, # Downwind distance (m)
    y: float, # Crosswind distance (m)
    z: float, # Receptor height (m)
    H: float, # Effective stack height (m)
    Q: float, # Emission rate (g/s)
    u: float, # Wind speed (m/s)
    stability_class: str
) -> float:
    """
    Forward Gaussian Plume Model (Classical Physics).
    Calculates downwind pollution concentration C(x,y,z).
    """
    if x <= 0 or u <= 0:
        return 0.0
        
    sigma_y, sigma_z = get_dispersion_parameters(x, stability_class)
    
    term1 = Q / (2 * math.pi * u * sigma_y * sigma_z)
    term2 = math.exp(- (y**2) / (2 * sigma_y**2))
    
    term3_a = math.exp(- ((z - H)**2) / (2 * sigma_z**2))
    term3_b = math.exp(- ((z + H)**2) / (2 * sigma_z**2))
    term3 = term3_a + term3_b
    
    concentration = term1 * term2 * term3
    return concentration # units: g/m^3

def calculate_source_triangulation(
    sensor_lat: float, 
    sensor_lon: float, 
    wind_dir_deg: float, 
    wind_speed: float
) -> Dict[str, Any]:
    """
    Source Triangulation: Back-calculates the likelihood cone of where the smoke originated
    up to 1-1.5 km upwind.
    wind_dir_deg is the meteorological wind direction (direction FROM WHICH the wind blows).
    """
    # Distance upwind based on wind speed (mocked logic: stronger wind = further cone)
    # Assume we track back for about 10-15 minutes (600-900 seconds)
    distance_m = min(wind_speed * 900, 1500) # max 1.5 km
    
    # The source is UPWIND, so it's in the direction of the wind origin
    # Meteorological wind direction is already where the wind is coming from.
    source_dir_rad = math.radians(wind_dir_deg)
    
    # Simple projection (1 deg lat/lon ~ 111km)
    lat_offset = (distance_m * math.cos(source_dir_rad)) / 111000.0
    lon_offset = (distance_m * math.sin(source_dir_rad)) / (111000.0 * math.cos(math.radians(sensor_lat)))
    
    predicted_source_lat = sensor_lat + lat_offset
    predicted_source_lon = sensor_lon + lon_offset
    
    return {
        "cone_origin": {"lat": sensor_lat, "lon": sensor_lon},
        "estimated_source": {"lat": predicted_source_lat, "lon": predicted_source_lon},
        "distance_m": distance_m,
        "spread_angle_deg": 30 # A +/- 15 degree cone
    }

def plume_inversion_pinn_mock(
    sensor_lat: float, 
    sensor_lon: float, 
    concentration: float, 
    wind_dir: float, 
    wind_speed: float, 
    temp: float
) -> Dict[str, Any]:
    """
    Plume Inversion / PINN (Physics-Informed Neural Network) proxy.
    Uses the single sensor's reading, wind vector, and temperature to solve 
    for the source location and emission rate (Q).
    """
    # In a real scenario, this would load a pre-trained PyTorch/TF model.
    # We will use the triangulation logic combined with an estimated Q
    triangulation = calculate_source_triangulation(sensor_lat, sensor_lon, wind_dir, wind_speed)
    
    # Rough estimate of Q based on observed concentration and distance
    # Inverting a simplified Gaussian model
    dist = triangulation["distance_m"]
    stability = determine_stability_class(wind_speed)
    sy, sz = get_dispersion_parameters(dist, stability)
    
    # Q = C * (2 * pi * u * sy * sz) (ignoring exp terms for rough order of magnitude)
    estimated_Q = concentration * (2 * math.pi * max(wind_speed, 1.0) * sy * sz)
    
    return {
        "source_lat": triangulation["estimated_source"]["lat"],
        "source_lon": triangulation["estimated_source"]["lon"],
        "emission_rate_Q": estimated_Q,
        "confidence": 0.85
    }
