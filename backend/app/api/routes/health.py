"""Health check (sección 36): backend + conexión a PostgreSQL."""
from __future__ import annotations

import json

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config import settings
from app.database.session import engine

router = APIRouter(tags=["salud"])


@router.get("/health")
def health():
    """Comprueba el backend y la conexión a la base de datos.

    Respuesta esperada: {"status": "ok", "database": "ok"}
    Si la BD no está disponible se refleja con estado 503.
    """
    database_status = "ok"
    status_code = 200
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        database_status = f"error: {exc.__class__.__name__}"
        status_code = 503

    body = {
        "status": "ok" if status_code == 200 else "error",
        "database": database_status,
        "app": settings.app_name,
        "version": settings.app_version,
    }
    return Response(
        content=json.dumps(body),
        status_code=status_code,
        media_type="application/json",
    )
