"""
Aervia Air Quality Index (AQI) Calculation Standards.
Implements:
1. India National Air Quality Index (NAQI) - CPCB 2014 Guidelines.
2. US EPA Air Quality Index - 40 CFR Part 58 Guidelines.
"""
from typing import Dict, Any, Optional, Tuple

# =====================================================================
# 1. INDIA NATIONAL AIR QUALITY INDEX (CPCB 2014)
# =====================================================================
# Breakpoints: (B_lo, B_hi, I_lo, I_hi)
CPCB_BREAKPOINTS = {
    "pm25": [
        (0.0, 30.0, 0, 50),
        (30.1, 60.0, 51, 100),
        (60.1, 90.0, 101, 200),
        (90.1, 120.0, 201, 300),
        (120.1, 250.0, 301, 400),
        (250.1, 350.0, 401, 500),
    ],
    "pm10": [
        (0.0, 50.0, 0, 50),
        (50.1, 100.0, 51, 100),
        (100.1, 250.0, 101, 200),
        (250.1, 350.0, 201, 300),
        (350.1, 430.0, 301, 400),
        (430.1, 500.0, 401, 500),
    ],
    "no2": [
        (0.0, 40.0, 0, 50),
        (40.1, 80.0, 51, 100),
        (80.1, 180.0, 101, 200),
        (180.1, 280.0, 201, 300),
        (280.1, 400.0, 301, 400),
        (400.1, 500.0, 401, 500),
    ],
    "so2": [
        (0.0, 40.0, 0, 50),
        (40.1, 80.0, 51, 100),
        (80.1, 380.0, 101, 200),
        (380.1, 800.0, 201, 300),
        (800.1, 1600.0, 301, 400),
        (1600.1, 2000.0, 401, 500),
    ],
    "co": [
        (0.0, 1.0, 0, 50),
        (1.01, 2.0, 51, 100),
        (2.01, 10.0, 101, 200),
        (10.01, 17.0, 201, 300),
        (17.01, 34.0, 301, 400),
        (34.01, 50.0, 401, 500),
    ],
    "o3": [
        (0.0, 50.0, 0, 50),
        (50.1, 100.0, 51, 100),
        (100.1, 168.0, 101, 200),
        (168.1, 208.0, 201, 300),
        (208.1, 748.0, 301, 400),
        (748.1, 1000.0, 401, 500),
    ],
    "nh3": [
        (0.0, 200.0, 0, 50),
        (200.1, 400.0, 51, 100),
        (400.1, 800.0, 101, 200),
        (800.1, 1200.0, 201, 300),
        (1200.1, 1800.0, 301, 400),
        (1800.1, 2400.0, 401, 500),
    ],
}


def calc_cpcb_sub_index(pollutant: str, concentration: float) -> Optional[float]:
    """
    Computes CPCB sub-index for a single pollutant using linear interpolation.
    Safely normalizes units: CPCB breakpoints expect CO in mg/m³ while CAAQMS
    feeds frequently report CO in µg/m³.
    """
    if concentration is None or concentration < 0:
        return None

    c = float(concentration)
    pol = pollutant.lower()

    # CO Normalization:
    # Ambient outdoor CO is typically 0.2 to 3.0 mg/m³.
    # When CPCB / State PCB stations report values > 5.0 (e.g. 15 to 80),
    # the analyzer telemetry is in µg/m³. Convert µg/m³ -> mg/m³:
    if pol == "co":
        if c > 5.0:
            c = c / 1000.0

    brackets = CPCB_BREAKPOINTS.get(pol)
    if not brackets:
        return None

    for b_lo, b_hi, i_lo, i_hi in brackets:
        if b_lo <= c <= b_hi:
            sub = ((i_hi - i_lo) / (b_hi - b_lo)) * (c - b_lo) + i_lo
            return round(sub, 1)

    # Beyond upper bracket -> severe cap at 500
    if c > brackets[-1][1]:
        return 500.0
    return 0.0


def calc_india_naqi(
    pm25: Optional[float] = None,
    pm10: Optional[float] = None,
    no2: Optional[float] = None,
    so2: Optional[float] = None,
    co: Optional[float] = None,
    o3: Optional[float] = None,
    nh3: Optional[float] = None,
) -> Tuple[Optional[float], Optional[str], Dict[str, float]]:
    """
    Calculates overall India National Air Quality Index (CPCB 2014 standard).
    Follows CPCB guideline: primary pollutant is the highest sub-index,
    requiring valid particulate monitoring (PM2.5 or PM10).
    Returns: (overall_aqi, primary_pollutant, sub_indices_dict)
    """
    candidates = {
        "PM2.5": calc_cpcb_sub_index("pm25", pm25) if pm25 is not None else None,
        "PM10": calc_cpcb_sub_index("pm10", pm10) if pm10 is not None else None,
        "NO2": calc_cpcb_sub_index("no2", no2) if no2 is not None else None,
        "SO2": calc_cpcb_sub_index("so2", so2) if so2 is not None else None,
        "CO": calc_cpcb_sub_index("co", co) if co is not None else None,
        "O3": calc_cpcb_sub_index("o3", o3) if o3 is not None else None,
        "NH3": calc_cpcb_sub_index("nh3", nh3) if nh3 is not None else None,
    }

    has_particulate = (pm25 is not None and pm25 > 0) or (pm10 is not None and pm10 > 0)
    valid_subs = {k: v for k, v in candidates.items() if v is not None}
    if not valid_subs or not has_particulate:
        return None, None, valid_subs

    # Primary pollutant is the one with the maximum sub-index
    primary_pollutant = max(valid_subs, key=valid_subs.get)
    overall_aqi = round(valid_subs[primary_pollutant], 1)

    return overall_aqi, primary_pollutant, valid_subs


def get_cpcb_category(aqi: float) -> Dict[str, Any]:
    """
    Returns official CPCB category and color for India NAQI.
    """
    if aqi is None:
        return {"category": "Unknown", "color": "#9ca3af", "level": 0}
    if aqi <= 50:
        return {"category": "Good", "color": "#00b050", "level": 1}
    elif aqi <= 100:
        return {"category": "Satisfactory", "color": "#92d050", "level": 2}
    elif aqi <= 200:
        return {"category": "Moderate", "color": "#ffff00", "level": 3}
    elif aqi <= 300:
        return {"category": "Poor", "color": "#ff9900", "level": 4}
    elif aqi <= 400:
        return {"category": "Very Poor", "color": "#ff0000", "level": 5}
    else:
        return {"category": "Severe", "color": "#c00000", "level": 6}


# =====================================================================
# 2. US EPA AIR QUALITY INDEX (40 CFR PART 58)
# =====================================================================
EPA_BREAKPOINTS = {
    "pm25": [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ],
    "pm10": [
        (0.0, 54.0, 0, 50),
        (55.0, 154.0, 51, 100),
        (155.0, 254.0, 101, 150),
        (255.0, 354.0, 151, 200),
        (355.0, 424.0, 201, 300),
        (425.0, 504.0, 301, 400),
        (505.0, 604.0, 401, 500),
    ],
    "no2": [
        (0.0, 53.0, 0, 50),
        (54.0, 100.0, 51, 100),
        (101.0, 360.0, 101, 150),
        (361.0, 649.0, 151, 200),
        (650.0, 1249.0, 201, 300),
        (1250.0, 2049.0, 301, 500),
    ],
    "so2": [
        (0.0, 35.0, 0, 50),
        (36.0, 75.0, 51, 100),
        (76.0, 185.0, 101, 150),
        (186.0, 304.0, 151, 200),
        (305.0, 604.0, 201, 300),
        (605.0, 1004.0, 301, 500),
    ],
    "co": [
        (0.0, 4.4, 0, 50),
        (4.5, 9.4, 51, 100),
        (9.5, 12.4, 101, 150),
        (12.5, 15.4, 151, 200),
        (15.5, 30.4, 201, 300),
        (30.5, 50.4, 301, 500),
    ],
    "o3": [
        (0.0, 54.0, 0, 50),
        (55.0, 70.0, 51, 100),
        (71.0, 85.0, 101, 150),
        (86.0, 105.0, 151, 200),
        (106.0, 200.0, 201, 300),
        (201.0, 600.0, 301, 500),
    ],
}


def calc_epa_sub_index(pollutant: str, concentration: float) -> Optional[float]:
    """
    Computes US EPA sub-index for a single pollutant using linear interpolation.
    Safely normalizes units from metric/CPCB feeds to EPA standard units:
    - PM2.5: µg/m³ (native)
    - PM10: µg/m³ (native)
    - CO: ppm (converts from µg/m³ or mg/m³)
    - NO2: ppb (converts from µg/m³: 1 ppb ≈ 1.88 µg/m³)
    - SO2: ppb (converts from µg/m³: 1 ppb ≈ 2.62 µg/m³)
    - O3: ppb (converts from µg/m³: 1 ppb ≈ 2.0 µg/m³)
    """
    if concentration is None or concentration < 0:
        return None

    c = float(concentration)
    pol = pollutant.lower()

    # Unit Normalizations:
    if pol == "co":
        if c > 5.0:
            c = c / 1145.0  # µg/m³ -> ppm
        elif c > 1.0:
            c = c * 0.873   # mg/m³ -> ppm
    elif pol == "no2":
        # CAAQMS reports in µg/m³; EPA breakpoints are in ppb
        c = c / 1.88
    elif pol == "so2":
        # CAAQMS reports in µg/m³; EPA breakpoints are in ppb
        c = c / 2.62
    elif pol == "o3":
        # CAAQMS reports in µg/m³; EPA breakpoints are in ppb
        c = c / 2.0

    brackets = EPA_BREAKPOINTS.get(pol)
    if not brackets:
        return None

    for b_lo, b_hi, i_lo, i_hi in brackets:
        if b_lo <= c <= b_hi:
            sub = ((i_hi - i_lo) / (b_hi - b_lo)) * (c - b_lo) + i_lo
            return round(sub, 1)

    if c > brackets[-1][1]:
        return 500.0
    return 0.0


def calc_us_epa_aqi(
    pm25: Optional[float] = None,
    pm10: Optional[float] = None,
    no2: Optional[float] = None,
    so2: Optional[float] = None,
    co: Optional[float] = None,
    o3: Optional[float] = None,
) -> Tuple[Optional[float], Optional[str], Dict[str, float]]:
    """
    Calculates overall US EPA AQI (40 CFR Part 58).
    Returns: (overall_aqi, primary_pollutant, sub_indices_dict)
    """
    candidates = {
        "PM2.5": calc_epa_sub_index("pm25", pm25) if pm25 is not None else None,
        "PM10": calc_epa_sub_index("pm10", pm10) if pm10 is not None else None,
        "NO2": calc_epa_sub_index("no2", no2) if no2 is not None else None,
        "SO2": calc_epa_sub_index("so2", so2) if so2 is not None else None,
        "CO": calc_epa_sub_index("co", co) if co is not None else None,
        "O3": calc_epa_sub_index("o3", o3) if o3 is not None else None,
    }

    has_particulate = (pm25 is not None and pm25 > 0) or (pm10 is not None and pm10 > 0)
    valid_subs = {k: v for k, v in candidates.items() if v is not None}
    if not valid_subs or not has_particulate:
        return None, None, valid_subs

    primary_pollutant = max(valid_subs, key=valid_subs.get)
    overall_aqi = round(valid_subs[primary_pollutant], 1)

    return overall_aqi, primary_pollutant, valid_subs


def get_epa_category(aqi: float) -> Dict[str, Any]:
    """
    Returns official US EPA category and color.
    """
    if aqi is None:
        return {"category": "Unknown", "color": "#9ca3af", "level": 0}
    if aqi <= 50:
        return {"category": "Good", "color": "#00e400", "level": 1}
    elif aqi <= 100:
        return {"category": "Moderate", "color": "#ffff00", "level": 2}
    elif aqi <= 150:
        return {"category": "Unhealthy for Sensitive Groups", "color": "#ff7e00", "level": 3}
    elif aqi <= 200:
        return {"category": "Unhealthy", "color": "#ff0000", "level": 4}
    elif aqi <= 300:
        return {"category": "Very Unhealthy", "color": "#8f3f97", "level": 5}
    else:
        return {"category": "Hazardous", "color": "#7e0023", "level": 6}
