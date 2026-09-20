"""Agregación de routers bajo /api."""
from fastapi import APIRouter

from app.api.routes import (
    backup_router,
    consumption_router,
    devices_router,
    imports_router,
    rates_router,
    reports_router,
    settings_router,
)

api_router = APIRouter()
api_router.include_router(devices_router)
api_router.include_router(imports_router)
api_router.include_router(consumption_router)
api_router.include_router(rates_router)
api_router.include_router(reports_router)
api_router.include_router(backup_router)
api_router.include_router(settings_router)
