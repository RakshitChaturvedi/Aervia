import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from dotenv import load_dotenv

# Load the repository-root env file before importing app modules that read
# configuration at module import time. Docker Compose injects env vars directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.database import engine, Base
from app.routers import api_router
from app.routers.sync import router as sync_router
from app.routers.auth import router as auth_router, seed_default_users
from app.redis_client import get_cache_status

from app.ingestion.scheduler import (
    start_ingestion_scheduler,
    stop_ingestion_scheduler,
    router as ingestion_router,
)
from app.iot_service import iot_service

# Initialize database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed initial RBAC demonstration accounts
    try:
        seed_default_users()
    except Exception as e:
        print(f"Warning: could not seed default users: {e}")

    # Startup: Start the background 15-minute CPCB/OpenAQ ingestion scheduler
    start_ingestion_scheduler(interval_seconds=900)

    # Startup: Connect to AWS IoT Core MQTT streams
    try:
        iot_service.start()
    except Exception as e:
        print(f"Warning: could not start AWS IoT Core service: {e}")

    yield
    # Shutdown: cancel background scheduler thread gracefully
    stop_ingestion_scheduler()
    iot_service.stop()


app = FastAPI(
    title="Aervia API Server",
    description="Enterprise Municipal Air Quality Intelligence Platform with 4-Tier RBAC, Time-Series Hypertables, and Distributed Caching.",
    version="2.0.0",
    lifespan=lifespan
)

# Allowed CORS origins (defaults to local frontend, configurable via ALLOWED_ORIGINS env)
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
if "*" in raw_origins:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Enterprise Security Headers & Data Sovereignty Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Data-Sovereignty-Region"] = "ap-south-1 (Mumbai, India)"
    response.headers["X-Compliance"] = "MeitY / DPDP Act 2023"
    return response


# Register routers
app.include_router(auth_router, prefix="/api")
app.include_router(api_router, prefix="/api")
app.include_router(api_router)
app.include_router(sync_router, prefix="/api")
app.include_router(ingestion_router)


@app.get("/")
def read_root():
    return {
        "platform": "Aervia 2.0 Enterprise API",
        "status": "online",
        "data_sovereignty_region": "ap-south-1 (Mumbai, India)",
        "docs_url": "/docs"
    }
