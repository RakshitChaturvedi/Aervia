"""
OpenAQ v3 Ingestion Worker for Aervia.
Fetches Indian ambient air quality monitoring telemetry from OpenAQ v3 API
as a high-speed fallback and secondary sensor validation network.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

from app.database import SessionLocal, Base, engine
from app.models import Station, StationObservation
from app.aqi_standards import calc_india_naqi, calc_us_epa_aqi
from app.ingestion.cpcb_worker import slugify

load_dotenv()

logger = logging.getLogger("openaq_worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")
BASE_URL = "https://api.openaq.org/v3"
INDIA_COUNTRY_ID = 9  # Verified OpenAQ v3 country ID for India

def fetch_openaq_locations(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetches list of active monitoring stations in India from OpenAQ v3."""
    if not OPENAQ_API_KEY:
        logger.warning("OPENAQ_API_KEY not found in environment.")
        return []

    url = f"{BASE_URL}/locations?countries_id={INDIA_COUNTRY_ID}&limit={limit}"
    headers = {
        "X-API-Key": OPENAQ_API_KEY,
        "User-Agent": "Aervia/1.0 (Contact: admin@aervia.in)",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.error(f"OpenAQ returned status {resp.status_code}: {resp.text[:200]}")
            return []
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        logger.error(f"Failed to query OpenAQ locations: {e}")
        return []

def fetch_location_latest(location_id: int) -> List[Dict[str, Any]]:
    """Fetches latest sensor readings for a specific OpenAQ location."""
    url = f"{BASE_URL}/locations/{location_id}/latest"
    headers = {
        "X-API-Key": OPENAQ_API_KEY,
        "User-Agent": "Aervia/1.0",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("results", [])
    except Exception:
        pass
    return []

def run_openaq_ingestion(max_locations: int = 30) -> Dict[str, Any]:
    """
    Ingests latest sensor observations from OpenAQ v3.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    stats = {
        "locations_scanned": 0,
        "stations_synced": 0,
        "observations_saved": 0,
        "errors": 0,
    }

    try:
        locations = fetch_openaq_locations(limit=max_locations)
        stats["locations_scanned"] = len(locations)
        logger.info(f"Retrieved {len(locations)} locations from OpenAQ v3.")

        for loc in locations:
            loc_id = loc.get("id")
            name = loc.get("name") or f"OpenAQ Station {loc_id}"
            coords = loc.get("coordinates") or {}
            lat = float(coords.get("latitude") or 0.0)
            lon = float(coords.get("longitude") or 0.0)

            # Determine city/state heuristics from station name or bounds
            city = "India"
            for known in ["Delhi", "Hyderabad", "Bengaluru", "Mumbai", "Kolkata", "Chennai", "Kanpur", "Pune"]:
                if known.lower() in name.lower():
                    city = known
                    break

            station_id = f"OPENAQ_{loc_id}_{slugify(name)[:30]}"
            station = db.query(Station).filter(Station.id == station_id).first()
            if not station:
                station = Station(
                    id=station_id,
                    name=name,
                    city=city,
                    state="India",
                    latitude=lat,
                    longitude=lon,
                    agency="OpenAQ",
                    source="openaq",
                    is_active=True,
                )
                db.add(station)
                db.flush()
                stats["stations_synced"] += 1

            # Fetch latest telemetry for this station
            latest_readings = fetch_location_latest(loc_id)
            if not latest_readings:
                continue

            pollutants: Dict[str, float] = {}
            obs_time = datetime.utcnow()

            for item in latest_readings:
                param = item.get("parameter", {}).get("name", "").lower()
                val = item.get("value")
                dt_str = item.get("datetime", {}).get("utc")
                if dt_str:
                    try:
                        obs_time = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    except Exception:
                        pass

                if val is not None and val >= 0:
                    pollutants[param] = float(val)

            pm25 = pollutants.get("pm25")
            pm10 = pollutants.get("pm10")
            no2 = pollutants.get("no2")
            so2 = pollutants.get("so2")
            co = pollutants.get("co")
            o3 = pollutants.get("o3")

            aqi_in, primary_pol, _ = calc_india_naqi(
                pm25=pm25, pm10=pm10, no2=no2, so2=so2, co=co, o3=o3
            )
            aqi_us, _, _ = calc_us_epa_aqi(
                pm25=pm25, pm10=pm10, no2=no2, so2=so2, co=co, o3=o3
            )

            # Check existing observation
            obs = (
                db.query(StationObservation)
                .filter(
                    StationObservation.station_id == station_id,
                    StationObservation.timestamp == obs_time,
                )
                .first()
            )
            if not obs:
                obs = StationObservation(
                    station_id=station_id,
                    timestamp=obs_time,
                    pm25=pm25,
                    pm10=pm10,
                    no2=no2,
                    so2=so2,
                    co=co,
                    o3=o3,
                    aqi_in=aqi_in,
                    aqi_us=aqi_us,
                    primary_pollutant=primary_pol,
                    source="openaq",
                    raw_payload=latest_readings,
                )
                db.add(obs)
                stats["observations_saved"] += 1

        db.commit()
        logger.info(
            f"OpenAQ Ingestion completed: {stats['stations_synced']} stations synced, "
            f"{stats['observations_saved']} observations saved."
        )
    except Exception as e:
        db.rollback()
        stats["errors"] += 1
        logger.error(f"OpenAQ ingestion error: {e}", exc_info=True)
    finally:
        db.close()

    return stats

if __name__ == "__main__":
    print("Running OpenAQ v3 Ingestion Worker...")
    res = run_openaq_ingestion(max_locations=10)
    print("OpenAQ Ingestion Results:", json.dumps(res, indent=2))
