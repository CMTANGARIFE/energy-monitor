"""Rutas de la API de Energy Monitor."""
from app.api.routes.backup import router as backup_router
from app.api.routes.consumption import router as consumption_router
from app.api.routes.devices import router as devices_router
from app.api.routes.health import router as health_router
from app.api.routes.imports import router as imports_router
from app.api.routes.rates import router as rates_router
from app.api.routes.reports import router as reports_router
from app.api.routes.settings_info import router as settings_router

__all__ = [
    "backup_router",
    "consumption_router",
    "devices_router",
    "health_router",
    "imports_router",
    "rates_router",
    "reports_router",
    "settings_router",
]
