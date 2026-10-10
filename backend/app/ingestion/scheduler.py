"""
Pipeline Scheduler & Ingestion Trigger Router for Aervia.
Provides background scheduled ingestion every 15-20 minutes
and an on-demand administrative manual sync endpoint.
"""
import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.database import SessionLocal
from app.models import Station, StationObservation
from app.ingestion.cpcb_worker import run_cpcb_ingestion
from app.ingestion.openaq_worker import run_openaq_ingestion

logger = logging.getLogger("ingestion_scheduler")

router = APIRouter(prefix="/api/ingestion", tags=["Ingestion"])

# Global scheduler state
INGESTION_STATUS = {
    "is_running": False,
    "last_run_time": None,
    "last_result": None,
    "total_runs": 0,
}
SCHEDULER_THREAD = None
RUN_EVENT = threading.Event()

def execute_ingestion_cycle() -> Dict[str, Any]:
    """Runs one full ingestion cycle across CPCB and OpenAQ."""
    global INGESTION_STATUS
    if INGESTION_STATUS["is_running"]:
        return {"status": "skipped", "reason": "Already running"}

    INGESTION_STATUS["is_running"] = True
    start_time = time.time()
    try:
        logger.info("Executing periodic ambient air quality ingestion cycle...")
        # 1. CPCB CAAQMS ingestion for all major monitored cities
        cpcb_stats = run_cpcb_ingestion()
        
        # 2. OpenAQ v3 backup ingestion
        openaq_stats = run_openaq_ingestion(max_locations=20)

        elapsed = round(time.time() - start_time, 2)
        result = {
            "status": "success",
            "cpcb": cpcb_stats,
            "openaq": openaq_stats,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.utcnow().isoformat(),
        }
        INGESTION_STATUS["last_run_time"] = datetime.utcnow().isoformat()
        INGESTION_STATUS["last_result"] = result
        INGESTION_STATUS["total_runs"] += 1
        logger.info(f"Ingestion cycle completed in {elapsed}s.")
        return result
    except Exception as e:
        logger.error(f"Ingestion cycle failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        INGESTION_STATUS["is_running"] = False

def scheduler_worker(interval_seconds: int = 900):
    """Background thread runner looping every interval_seconds (15 min)."""
    logger.info(f"Ingestion background scheduler started (cadence: {interval_seconds}s).")
    # Wait 30 seconds after server boot before first background cycle to let API stabilize
    time.sleep(30)
    while not RUN_EVENT.is_set():
        try:
            execute_ingestion_cycle()
        except Exception as e:
            logger.error(f"Scheduler worker encounter: {e}")
        # Sleep in chunks to allow responsive shutdown
        for _ in range(interval_seconds // 5):
            if RUN_EVENT.is_set():
                break
            time.sleep(5)

def start_ingestion_scheduler(interval_seconds: int = 900):
    """Starts the background scheduler thread."""
    global SCHEDULER_THREAD
    if SCHEDULER_THREAD is None or not SCHEDULER_THREAD.is_alive():
        RUN_EVENT.clear()
        SCHEDULER_THREAD = threading.Thread(
            target=scheduler_worker,
            args=(interval_seconds,),
            daemon=True,
            name="Aervia-IngestionScheduler",
        )
        SCHEDULER_THREAD.start()

def stop_ingestion_scheduler():
    """Stops the scheduler thread gracefully."""
    RUN_EVENT.set()

@router.post("/trigger")
def trigger_manual_ingestion(background_tasks: BackgroundTasks):
    """
    On-demand administrative trigger to run an immediate ingestion cycle.
    """
    if INGESTION_STATUS["is_running"]:
        return {"message": "Ingestion cycle is currently in progress", "status": INGESTION_STATUS}

    background_tasks.add_task(execute_ingestion_cycle)
    return {
        "message": "Ingestion cycle triggered in background",
        "timestamp": datetime.utcnow().isoformat(),
    }

@router.get("/status")
def get_ingestion_status():
    """
    Returns current database station metrics, total observations, and last sync details.
    """
    db = SessionLocal()
    try:
        station_count = db.query(Station).count()
        observation_count = db.query(StationObservation).count()
        latest_obs = (
            db.query(StationObservation)
            .order_by(StationObservation.timestamp.desc())
            .first()
        )
        latest_ts = latest_obs.timestamp.isoformat() if latest_obs else None

        return {
            "scheduler_active": SCHEDULER_THREAD is not None and SCHEDULER_THREAD.is_alive(),
            "scheduler_status": INGESTION_STATUS,
            "metrics": {
                "total_monitored_stations": station_count,
                "total_observations": observation_count,
                "latest_observation_time": latest_ts,
            },
        }
    finally:
        db.close()
