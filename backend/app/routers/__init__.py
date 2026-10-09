from fastapi import APIRouter
from app.routers.ingest import router as ingest_router
from app.routers.forecast import router as forecast_router
from app.routers.attribution import router as attribution_router
from app.routers.optimize import router as optimize_router
from app.routers.health import router as health_router
from app.routers.live import router as live_router
from app.routers.satellite import router as satellite_router
from app.routers.notifications import router as notifications_router
from app.routers.report import router as report_router
from app.routers.atmospheric_forecast import router as atmospheric_forecast_router
from app.routers.stubble_plume import router as stubble_plume_router

api_router = APIRouter()

api_router.include_router(ingest_router)
api_router.include_router(forecast_router)
api_router.include_router(attribution_router)
api_router.include_router(optimize_router)
api_router.include_router(health_router)
api_router.include_router(live_router)
api_router.include_router(satellite_router)
api_router.include_router(notifications_router)
api_router.include_router(report_router)
api_router.include_router(atmospheric_forecast_router)
api_router.include_router(stubble_plume_router)
