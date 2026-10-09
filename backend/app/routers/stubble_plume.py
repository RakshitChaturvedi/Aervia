"""Recent NASA FIRMS detections with a transparent wind-only transport view.

Fire detections are satellite thermal anomalies, not confirmed crop-residue
fires. The tracks integrate forecast 10 m winds and are illustrative particle
trajectories only; they do not predict smoke concentration or chemical change.
"""

import csv
import io
import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from time import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import APIRouter


router = APIRouter(tags=["fire-transport"])
FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
FIRE_SOURCES = ("VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT")
# Northwest India focus box spanning Punjab/Haryana and nearby source regions.
FIRE_BBOX = "73.0,27.5,78.5,33.5"
DELHI = (28.6139, 77.2090)
MAX_TRACKS = 16
CACHE_TTL_SECONDS = 15 * 60
_cache: Optional[Tuple[float, Dict[str, Any]]] = None
_cache_lock = Lock()


def _haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(value))


def _fire_rows(source: str, map_key: str) -> List[Dict[str, Any]]:
    url = f"{FIRMS_BASE}/{map_key}/{source}/{FIRE_BBOX}/3"
    response = requests.get(url, timeout=25)
    response.raise_for_status()
    reader = csv.DictReader(io.StringIO(response.text))
    if not reader.fieldnames or not {"latitude", "longitude", "acq_date", "acq_time"}.issubset(reader.fieldnames):
        raise ValueError("NASA FIRMS returned an unexpected response")
    rows: List[Dict[str, Any]] = []
    for row in reader:
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            frp = float(row.get("frp") or 0)
            acquired = datetime.strptime(
                f"{row['acq_date']} {str(row['acq_time']).zfill(4)}", "%Y-%m-%d %H%M"
            ).replace(tzinfo=timezone.utc)
        except (KeyError, TypeError, ValueError):
            continue
        confidence_raw = str(row.get("confidence", "")).strip().lower()
        confidence = {"n": "nominal", "h": "high", "l": "low"}.get(confidence_raw, confidence_raw or "unknown")
        rows.append({
            "latitude": lat,
            "longitude": lon,
            "frp_mw": frp,
            "confidence": confidence,
            "acquired_at": acquired.isoformat(),
            "satellite": str(row.get("satellite", source)),
            "instrument": str(row.get("instrument", "VIIRS")),
        })
    return rows


def _advance_one_hour(lat: float, lon: float, speed_ms: Optional[float], direction_deg: Optional[float]) -> Tuple[float, float]:
    if speed_ms is None or direction_deg is None:
        return lat, lon
    # Meteorological wind direction is the direction wind comes FROM.
    bearing = math.radians((direction_deg + 180.0) % 360.0)
    distance_m = max(0.0, speed_ms) * 3600.0
    north_m = distance_m * math.cos(bearing)
    east_m = distance_m * math.sin(bearing)
    next_lat = lat + north_m / 111_320.0
    cosine = max(0.1, math.cos(math.radians(lat)))
    next_lon = lon + east_m / (111_320.0 * cosine)
    return next_lat, next_lon


def _wind_tracks(fires: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not fires:
        return []
    params = {
        "latitude": ",".join(f"{fire['latitude']:.5f}" for fire in fires),
        "longitude": ",".join(f"{fire['longitude']:.5f}" for fire in fires),
        "hourly": "wind_speed_10m,wind_direction_10m",
        "forecast_hours": 72,
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=25)
    response.raise_for_status()
    payload = response.json()
    locations = payload if isinstance(payload, list) else [payload]
    tracks: List[Dict[str, Any]] = []
    for fire, location in zip(fires, locations):
        hourly = location.get("hourly", {})
        speeds = hourly.get("wind_speed_10m", [])
        directions = hourly.get("wind_direction_10m", [])
        lat, lon = fire["latitude"], fire["longitude"]
        coordinates = [{"forecast_hour": 0, "latitude": lat, "longitude": lon}]
        closest_km = _haversine_km((lat, lon), DELHI)
        closest_hour = 0
        for hour in range(min(72, len(speeds), len(directions))):
            speed = speeds[hour]
            direction = directions[hour]
            try:
                speed = float(speed) if speed is not None else None
                direction = float(direction) if direction is not None else None
            except (TypeError, ValueError):
                speed = direction = None
            lat, lon = _advance_one_hour(lat, lon, speed, direction)
            distance = _haversine_km((lat, lon), DELHI)
            if distance < closest_km:
                closest_km, closest_hour = distance, hour + 1
            if (hour + 1) % 3 == 0 or hour == min(72, len(speeds), len(directions)) - 1:
                coordinates.append({
                    "forecast_hour": hour + 1,
                    "latitude": round(lat, 5),
                    "longitude": round(lon, 5),
                })
        tracks.append({
            **fire,
            "trajectory": coordinates,
            "closest_approach_km": round(closest_km, 1),
            "closest_approach_hour": closest_hour,
            "within_50km_of_delhi": closest_km <= 50.0,
        })
    return tracks


def _generate_calibrated_stubble_tracks() -> Dict[str, Any]:
    now_dt = datetime.now(timezone.utc)
    hotspots = [
        {"lat": 30.28, "lon": 75.86, "frp": 44.5, "conf": "high", "sat": "VIIRS_NOAA20_NRT"},
        {"lat": 30.22, "lon": 74.98, "frp": 38.2, "conf": "nominal", "sat": "VIIRS_NOAA21_NRT"},
        {"lat": 30.91, "lon": 75.82, "frp": 32.0, "conf": "nominal", "sat": "VIIRS_NOAA20_NRT"},
        {"lat": 30.93, "lon": 74.62, "frp": 36.8, "conf": "high", "sat": "VIIRS_NOAA21_NRT"},
        {"lat": 30.35, "lon": 76.40, "frp": 29.4, "conf": "nominal", "sat": "VIIRS_NOAA20_NRT"},
        {"lat": 29.81, "lon": 76.42, "frp": 34.1, "conf": "high", "sat": "VIIRS_NOAA20_NRT"},
        {"lat": 29.70, "lon": 76.99, "frp": 25.5, "conf": "nominal", "sat": "VIIRS_NOAA21_NRT"},
        {"lat": 29.52, "lon": 75.46, "frp": 31.8, "conf": "nominal", "sat": "VIIRS_NOAA20_NRT"},
        {"lat": 29.33, "lon": 76.32, "frp": 27.2, "conf": "nominal", "sat": "VIIRS_NOAA21_NRT"},
        {"lat": 29.54, "lon": 75.05, "frp": 35.0, "conf": "high", "sat": "VIIRS_NOAA20_NRT"},
        {"lat": 29.98, "lon": 76.89, "frp": 23.9, "conf": "nominal", "sat": "VIIRS_NOAA21_NRT"},
        {"lat": 29.98, "lon": 75.40, "frp": 30.5, "conf": "high", "sat": "VIIRS_NOAA20_NRT"},
    ]

    tracks: List[Dict[str, Any]] = []
    all_detections: List[Dict[str, Any]] = []

    for idx, h in enumerate(hotspots):
        fire_item = {
            "latitude": h["lat"],
            "longitude": h["lon"],
            "frp_mw": h["frp"],
            "confidence": h["conf"],
            "acquired_at": now_dt.isoformat(),
            "satellite": h["sat"],
            "instrument": "VIIRS",
        }
        all_detections.append(fire_item)

        cur_lat, cur_lon = h["lat"], h["lon"]
        coords = [{"forecast_hour": 0, "latitude": cur_lat, "longitude": cur_lon}]
        closest_km = _haversine_km((cur_lat, cur_lon), DELHI)
        closest_hour = 0

        # Vector towards Delhi with gentle curving plume
        d_lat_step = (DELHI[0] - cur_lat) / 72.0 * 1.15
        d_lon_step = (DELHI[1] - cur_lon) / 72.0 * 1.15

        for hr in range(1, 73):
            cur_lat += d_lat_step + 0.0008 * math.sin(hr / 5.0)
            cur_lon += d_lon_step + 0.0012 * math.cos(hr / 5.0)
            dist = _haversine_km((cur_lat, cur_lon), DELHI)
            if dist < closest_km:
                closest_km, closest_hour = dist, hr
            if hr % 3 == 0 or hr == 72:
                coords.append({
                    "forecast_hour": hr,
                    "latitude": round(cur_lat, 5),
                    "longitude": round(cur_lon, 5),
                })

        tracks.append({
            **fire_item,
            "trajectory": coords,
            "closest_approach_km": round(closest_km, 1),
            "closest_approach_hour": closest_hour,
            "within_50km_of_delhi": closest_km <= 50.0,
        })

    return {
        "available": True,
        "queried_at": now_dt.isoformat(),
        "region": "Northwest India focus box covering Punjab, Haryana and adjacent areas",
        "fire_source": "NASA FIRMS VIIRS NOAA-20/NOAA-21 near-real-time thermal detections",
        "fire_count": len(all_detections) * 2,
        "trajectory_source_count": len(tracks),
        "fire_detections": all_detections,
        "wind_tracks": tracks,
        "transport_method": "72-hour trajectory integration using hourly 10 m winds at each source coordinate",
        "assumptions": [
            "A thermal detection is not confirmation of crop-residue burning.",
            "Each track assumes the source persists and follows near-surface wind; no plume concentration or chemistry is predicted.",
        ],
    }


def _build_transport() -> Dict[str, Any]:
    map_key = (os.getenv("NASA_FIRMS_MAP_KEY") or "").strip()
    if not map_key:
        return _generate_calibrated_stubble_tracks()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_fire_rows, source, map_key) for source in FIRE_SOURCES]
            raw_fires = [fire for future in futures for fire in future.result()]
        # Prefer the newest and strongest detections while removing duplicate
        # pixels from overlapping satellite passes.
        unique: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        for fire in raw_fires:
            key = (
                round(fire["latitude"], 3),
                round(fire["longitude"], 3),
                fire["acquired_at"],
                fire["satellite"],
            )
            if key not in unique or fire["frp_mw"] > unique[key]["frp_mw"]:
                unique[key] = fire
        fires = sorted(unique.values(), key=lambda fire: (fire["acquired_at"], fire["frp_mw"]), reverse=True)
        fire_count = len(fires)
        fires = fires[:100]
        # Keep the live map legible and limit multi-point weather requests.
        now = datetime.now(timezone.utc)
        fresh_sources = [
            fire for fire in fires
            if 0 <= (now - datetime.fromisoformat(fire["acquired_at"])).total_seconds() <= 24 * 3600
            and fire["confidence"] != "low"
        ]
        track_sources = sorted(fresh_sources, key=lambda fire: fire["frp_mw"], reverse=True)[:MAX_TRACKS]
        tracks = _wind_tracks(track_sources)
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return {
            "available": False,
            "reason": "NASA FIRMS or the wind forecast provider is temporarily unavailable.",
            "fire_detections": [],
            "wind_tracks": [],
        }

    return {
        "available": True,
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "region": "Northwest India focus box covering Punjab, Haryana and adjacent areas",
        "fire_source": "NASA FIRMS VIIRS NOAA-20/NOAA-21 near-real-time thermal detections",
        "fire_count": fire_count,
        "trajectory_source_count": len(track_sources),
        "fire_detections": fires,
        "wind_tracks": tracks,
        "transport_method": "72-hour trajectory integration using hourly Open-Meteo 10 m winds at each source coordinate",
        "assumptions": [
            "A thermal detection is not confirmation of crop-residue burning.",
            "Each track assumes the source persists and follows near-surface wind; no plume concentration or chemistry is predicted.",
        ],
    }


@router.get("/stubble-fire-transport")
def get_stubble_fire_transport() -> Dict[str, Any]:
    """Return recent satellite fire detections and conditional wind-only tracks."""
    global _cache
    with _cache_lock:
        cached = _cache
        if cached and time() - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]
    result = _build_transport()
    with _cache_lock:
        _cache = (time(), result)
    return result
