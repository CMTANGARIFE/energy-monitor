"""Energy Monitor - punto de entrada FastAPI.

- Configura logging, CORS y routers.
- Traduce errores de dominio a respuestas HTTP con mensajes claros
  (sección 46): el usuario nunca ve un "Internal Server Error" desnudo.
- Opcionalmente sirve el build del frontend (útil sin Docker);
  en producción Docker, nginx sirve el frontend y proxya /api.
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.api.routes import health_router
from app.config import settings
from app.logging_conf import setup_logging
from app.services.errors import ConflictError, NotFoundError, ValidationError

setup_logging()
logger = logging.getLogger("energy_monitor.main")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API REST para monitoreo y análisis de consumo energético diario.",
)

# CORS (aplicación local: por defecto se permite cualquier origen de la red local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(api_router, prefix="/api")


# ----------------------------------------------------------------------
# Manejo de errores con mensajes comprensibles (sección 46)
# ----------------------------------------------------------------------
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": exc.message})


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.message, "errors": exc.errors},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validación de request fallida: %s", exc.errors()[:3])
    return JSONResponse(
        status_code=422,
        content={"detail": "Datos de la solicitud inválidos. Verifique los campos enviados."},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("Error interno no controlado en %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error interno inesperado. "
                           "El detalle técnico quedó registrado en los logs del backend."},
    )


# ----------------------------------------------------------------------
# Fallback de esquema: crea tablas si la BD está totalmente vacía
# (el flujo normal de producción usa migraciones Alembic, ver entrypoint).
# ----------------------------------------------------------------------
@app.on_event("startup")
def ensure_schema() -> None:
    from sqlalchemy import inspect as sql_inspect

    from app.database.base import Base
    from app.database.session import engine

    try:
        inspector = sql_inspect(engine)
        existing = inspector.get_table_names()
        required = {"devices", "energy_consumption", "energy_rates", "import_history"}
        if not required.issubset(set(existing)):
            logger.warning("Esquema incompleto (%s). Aplicando create_all de respaldo. "
                           "En producción use: alembic upgrade head", existing)
            Base.metadata.create_all(bind=engine)
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo verificar el esquema de la base de datos.")


# ----------------------------------------------------------------------
# Servir frontend compilado cuando exista (modo sin Docker / demo local)
# ----------------------------------------------------------------------
FRONTEND_DIST = os.environ.get("FRONTEND_DIST", "")
_dist_dir = FRONTEND_DIST if FRONTEND_DIST and os.path.isdir(FRONTEND_DIST) else None

if _dist_dir:
    assets_dir = os.path.join(_dist_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="spa-assets")

    from fastapi.responses import FileResponse

    index_html = os.path.join(_dist_dir, "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """Sirve archivos estáticos del build o index.html (SPA)."""
        candidate = os.path.normpath(os.path.join(_dist_dir, full_path))
        if candidate.startswith(_dist_dir) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(index_html)

    logger.info("Sirviendo frontend desde %s", _dist_dir)
