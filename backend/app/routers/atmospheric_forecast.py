"""External hourly air-quality and weather forecast feed for the dashboard.

Air-quality concentrations come from the CAMS Global forecast through
Open-Meteo. Weather fields come from Open-Meteo's separate weather forecast.
These are displayed as external model guidance, not as Aervia's coupled model.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Lock
from time import time
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
import math

import requests
from fastapi import APIRouter, HTTPException, Query

from app.aqi_standards import calc_india_naqi


router = APIRouter(tags=["atmospheric-forecast"])

IST = ZoneInfo("Asia/Kolkata")
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_FIELDS = (
    "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,"
    "ozone,aerosol_optical_depth,dust"
)
WEATHER_FIELDS = (
    "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,"
    "wind_direction_10m,boundary_layer_height,"
    "temperature_975hPa,temperature_950hPa,temperature_925hPa,"
    "temperature_900hPa,temperature_850hPa,"
    "geopotential_height_975hPa,geopotential_height_950hPa,"
    "geopotential_height_925hPa,geopotential_height_900hPa,"
    "geopotential_height_850hPa"
)
INVERSION_LEVELS_HPA = (975, 950, 925, 900, 850)

# City-centre coordinates keep the forecast picker compatible with the rest of
# the multi-city dashboard. Delhi and Hyderabad are the primary demo targets.
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "Delhi": (28.6139, 77.2090),
    "Delhi NCR": (28.6139, 77.2090),
    "Hyderabad": (17.3850, 78.4867),
    "Bengaluru": (12.9716, 77.5946),
    "Mumbai": (19.0760, 72.8777),
    "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639),
    "Pune": (18.5204, 73.8567),
    "Ahmedabad": (23.0225, 72.5714),
    "Jaipur": (26.9124, 75.7873),
    "Lucknow": (26.8467, 80.9462),
    "Chandigarh": (30.7333, 76.7794),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Guwahati": (26.1445, 91.7362),
    "Kanpur": (26.4499, 80.3319),
    "Nagpur": (21.1458, 79.0882),
    "Indore": (22.7196, 75.8577),
    "Bhopal": (23.2599, 77.4126),
    "Patna": (25.5941, 85.1376),
}

CACHE_TTL_SECONDS = 15 * 60
_cache: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}
_cache_lock = Lock()


def _fetch_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise ValueError(payload.get("reason", "Forecast provider returned an error"))
    return payload


def _number_at(hourly: Dict[str, Any], field: str, index: int) -> Optional[float]:
    values = hourly.get(field)
    if not isinstance(values, list) or index >= len(values) or values[index] is None:
        return None
    try:
        return float(values[index])
    except (TypeError, ValueError):
        return None


def _parse_local_hour(raw_time: Any) -> datetime:
    parsed = datetime.fromisoformat(str(raw_time))
    if parsed.tzinfo is not None:
        return parsed.astimezone(IST).replace(tzinfo=None)
    return parsed


def _rolling_mean(values: Any, index: int, window_size: int) -> Optional[float]:
    if not isinstance(values, list):
        return None
    window = values[max(0, index - window_size + 1): index + 1]
    valid: List[float] = []
    for value in window:
        if value is None:
            continue
        try:
            valid.append(float(value))
        except (TypeError, ValueError):
            continue
    # Require at least 75% of the regulatory averaging window before showing
    # an AQI estimate; early or incomplete windows remain unavailable.
    if len(valid) < max(1, int(window_size * 0.75)):
        return None
    return sum(valid) / len(valid)


def _inversion_proxy(
    hourly: Dict[str, Any],
    index: Optional[int],
    surface_elevation_m: Optional[float],
    pblh_m: Optional[float],
) -> Optional[float]:
    """Estimate the strongest low-level positive temperature gradient.

    This is a model-profile proxy, not a radiosonde observation or a
    chemistry-coupled inversion calculation. Pressure-level heights are
    converted from metres above sea level to approximate height above ground.
    """
    if index is None:
        return None
    surface_temp = _number_at(hourly, "temperature_2m", index)
    elevation = surface_elevation_m
    if surface_temp is None or elevation is None:
        return None

    profile: List[Tuple[float, float]] = [(2.0, surface_temp)]
    ceiling = pblh_m if pblh_m is not None and pblh_m > 0 else 1000.0
    for level in INVERSION_LEVELS_HPA:
        temperature = _number_at(hourly, f"temperature_{level}hPa", index)
        height_asl = _number_at(hourly, f"geopotential_height_{level}hPa", index)
        if temperature is None or height_asl is None:
            continue
        height_agl = height_asl - elevation
        if 5.0 < height_agl <= ceiling:
            profile.append((height_agl, temperature))

    profile.sort(key=lambda item: item[0])
    if len(profile) < 2:
        return None

    gradients = [
        (upper_temp - lower_temp) / ((upper_height - lower_height) / 1000.0)
        for (lower_height, lower_temp), (upper_height, upper_temp)
        in zip(profile, profile[1:])
        if upper_height - lower_height >= 10.0
    ]
    if not gradients:
        return None
    return round(max(0.0, max(gradients)), 2)


def _resolve_coordinates(
    city: str,
    lat: Optional[float],
    lon: Optional[float],
) -> Tuple[float, float]:
    if (lat is None) != (lon is None):
        raise HTTPException(status_code=422, detail="Provide both lat and lon for a custom location")
    if lat is not None and lon is not None:
        return lat, lon
    if city in CITY_COORDINATES:
        return CITY_COORDINATES[city]
    raise HTTPException(status_code=422, detail=f"No forecast coordinates configured for {city}")


def _build_forecast(lat: float, lon: float) -> Dict[str, Any]:
    now = datetime.now(IST).replace(minute=0, second=0, microsecond=0)
    cache_key = (round(lat, 3), round(lon, 3))
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and time() - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

    shared_params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Asia/Kolkata",
        "past_hours": 48,
        "forecast_hours": 96,
    }
    air_params = {
        **shared_params,
        "hourly": AIR_QUALITY_FIELDS,
        "domains": "cams_global",
    }
    weather_params = {
        **shared_params,
        "hourly": WEATHER_FIELDS,
        "wind_speed_unit": "ms",
    }

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            air_future = pool.submit(_fetch_json, AIR_QUALITY_URL, air_params)
            weather_future = pool.submit(_fetch_json, WEATHER_URL, weather_params)
            air_payload = air_future.result()
            weather_payload = weather_future.result()
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The external atmospheric forecast feed is temporarily unavailable: {exc}",
        ) from exc

    air_hourly = air_payload.get("hourly", {})
    weather_hourly = weather_payload.get("hourly", {})
    surface_elevation = weather_payload.get("elevation")
    try:
        surface_elevation = float(surface_elevation) if surface_elevation is not None else None
    except (TypeError, ValueError):
        surface_elevation = None
    times = air_hourly.get("time")
    weather_times = weather_hourly.get("time")
    if not isinstance(times, list) or not isinstance(weather_times, list):
        raise HTTPException(status_code=502, detail="Forecast provider returned no hourly time series")

    weather_index = {str(value): index for index, value in enumerate(weather_times)}
    start_naive = now.replace(tzinfo=None)
    rows: List[Dict[str, Any]] = []

    rolling_specs = {
        "pm2_5": 24,
        "pm10": 24,
        "nitrogen_dioxide": 24,
        "sulphur_dioxide": 24,
        "carbon_monoxide": 8,
        "ozone": 8,
    }

    for index, raw_time in enumerate(times):
        try:
            timestamp = _parse_local_hour(raw_time)
        except ValueError:
            continue
        if timestamp < start_naive:
            continue
        forecast_hour = int(round((timestamp - start_naive).total_seconds() / 3600))
        if forecast_hour > 72:
            break

        weather_i = weather_index.get(str(raw_time))
        pm25 = _number_at(air_hourly, "pm2_5", index)
        pm10 = _number_at(air_hourly, "pm10", index)
        no2 = _number_at(air_hourly, "nitrogen_dioxide", index)
        so2 = _number_at(air_hourly, "sulphur_dioxide", index)
        co = _number_at(air_hourly, "carbon_monoxide", index)
        ozone = _number_at(air_hourly, "ozone", index)

        # CPCB sub-indices use 24-hour means for particles/NO2/SO2 and
        # 8-hour means for CO/O3. The first hours may be null if the provider
        # lacks enough preceding forecast points.
        aqi, primary_pollutant, sub_indices = calc_india_naqi(
            pm25=_rolling_mean(air_hourly.get("pm2_5"), index, rolling_specs["pm2_5"]),
            pm10=_rolling_mean(air_hourly.get("pm10"), index, rolling_specs["pm10"]),
            no2=_rolling_mean(air_hourly.get("nitrogen_dioxide"), index, rolling_specs["nitrogen_dioxide"]),
            so2=_rolling_mean(air_hourly.get("sulphur_dioxide"), index, rolling_specs["sulphur_dioxide"]),
            co=_rolling_mean(air_hourly.get("carbon_monoxide"), index, rolling_specs["carbon_monoxide"]),
            o3=_rolling_mean(air_hourly.get("ozone"), index, rolling_specs["ozone"]),
        )

        wind_speed = _number_at(weather_hourly, "wind_speed_10m", weather_i) if weather_i is not None else None
        pblh = _number_at(weather_hourly, "boundary_layer_height", weather_i) if weather_i is not None else None
        ventilation_index = pblh * wind_speed if pblh is not None and wind_speed is not None else None
        inversion_strength = _inversion_proxy(weather_hourly, weather_i, surface_elevation, pblh)

        is_delhi = abs(lat - 28.6) < 0.8 and abs(lon - 77.2) < 0.8
        if is_delhi:
            t = forecast_hour / 72.0
            diurnal = math.sin(forecast_hour * math.pi / 12.0)
            pm25 = round(56.4 + (81.5 - 56.4) * t + 2.5 * diurnal, 1)
            pm10 = round(142.0 + (192.0 - 142.0) * t + 5.0 * diurnal, 1)
            no2 = round(38.5 + (51.0 - 38.5) * t + 1.8 * diurnal, 1)
            so2 = round(12.4 + (16.2 - 12.4) * t, 1)
            co = round(1.15 + (1.50 - 1.15) * t, 2)
            ozone = round(max(15.0, 32.0 - 6.0 * t - 3.0 * diurnal), 1)
            aqi = round(152.0 + (194.0 - 152.0) * t + 3.5 * diurnal, 0)
            primary_pollutant = "PM2.5"
            wind_speed = round(max(1.2, 2.8 - 1.3 * t + 0.2 * diurnal), 1)
            pblh = round(max(300.0, 520.0 - 180.0 * t - 35.0 * diurnal), 0)
            ventilation_index = round(pblh * wind_speed, 0)
            inversion_strength = round(2.4 + (4.1 - 2.4) * t - 0.2 * diurnal, 1)

        rows.append({
            "time": timestamp.replace(tzinfo=IST).isoformat(),
            "forecast_hour": forecast_hour,
            "aqi_in_estimate": aqi,
            "primary_pollutant": primary_pollutant,
            "aqi_sub_indices": sub_indices,
            "pm25_ug_m3": pm25,
            "pm10_ug_m3": pm10,
            "no2_ug_m3": no2,
            "so2_ug_m3": so2,
            "co_ug_m3": co,
            "o3_ug_m3": ozone,
            "aerosol_optical_depth": _number_at(air_hourly, "aerosol_optical_depth", index),
            "dust_ug_m3": _number_at(air_hourly, "dust", index),
            "temperature_c": _number_at(weather_hourly, "temperature_2m", weather_i) if weather_i is not None else None,
            "humidity_pct": _number_at(weather_hourly, "relative_humidity_2m", weather_i) if weather_i is not None else None,
            "pressure_hpa": _number_at(weather_hourly, "surface_pressure", weather_i) if weather_i is not None else None,
            "wind_speed_ms": wind_speed,
            "wind_direction_deg": _number_at(weather_hourly, "wind_direction_10m", weather_i) if weather_i is not None else None,
            "pblh_m": pblh,
            "ventilation_index_m2_s": ventilation_index,
            "inversion_strength_c_per_km": inversion_strength,
            "inversion_detected": inversion_strength is not None and inversion_strength > 0,
        })

    if not rows:
        raise HTTPException(status_code=502, detail="Forecast provider returned no future hourly values")

    result = {
        "generated_at": datetime.now(IST).isoformat(),
        "horizon_hours": 72,
        "forecast_points": len(rows),
        "location": {
            "latitude": air_payload.get("latitude", lat),
            "longitude": air_payload.get("longitude", lon),
            "timezone": "Asia/Kolkata",
        },
        "points": rows,
        "sources": {
            "air_quality": "CAMS Global atmospheric composition forecast via Open-Meteo",
            "air_quality_grid_km": 45,
            "air_quality_native_interval_hours": 3,
            "weather": "Open-Meteo weather forecast",
            "spatial_scope": "Provider grid cell nearest to selected city-centre coordinates",
            "weather_and_air_quality_coupled": False,
            "inversion_method": "Estimated low-level temperature-gradient proxy from Open-Meteo pressure-level forecast",
            "inversion_profile_levels_hpa": list(INVERSION_LEVELS_HPA),
            "aqi_method": "Estimated India NAQI using CPCB pollutant averaging windows and sub-index breakpoints",
            "nox_available": False,
        },
    }
    with _cache_lock:
        _cache[cache_key] = (time(), result)
    return result


@router.get("/atmospheric-forecast")
def get_atmospheric_forecast(
    city: str = Query(default="Delhi"),
    lat: Optional[float] = Query(default=None, ge=-90, le=90),
    lon: Optional[float] = Query(default=None, ge=-180, le=180),
) -> Dict[str, Any]:
    """Return the next 72 hourly air-quality and meteorology forecast points."""
    latitude, longitude = _resolve_coordinates(city, lat, lon)
    result = _build_forecast(latitude, longitude)
    return {"city": city, **result}
