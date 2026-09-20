"""Backup de la base de datos (sección 39).

Estrategia:
- PostgreSQL (producción): se ejecuta `pg_dump` con las credenciales de
  DATABASE_URL y se devuelve el volcado SQL como descarga.
- Otros motores (desarrollo/tests): volcado JSON genérico de las tablas.

El procedimiento documentado con `docker compose exec postgres pg_dump`
está en docs/BACKUP.md.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import logging
import os
import shutil
import subprocess
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.database.session import engine

logger = logging.getLogger("energy_monitor.api.backup")
router = APIRouter(tags=["backup"])


@router.get("/backup")
def download_backup():
    """Descarga un respaldo completo de la base de datos.

    - PostgreSQL: volcado SQL estándar (pg_dump --no-owner --no-privileges).
    - Otros motores: volcado JSON.
    """
    url = settings.database_url
    if url.startswith("postgresql"):
        content, filename, media = _pg_dump_backup(url)
    else:
        content, filename, media = _json_backup()
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pg_dump_backup(url: str) -> tuple[bytes, str, str]:
    pg_dump = shutil.which("pg_dump")
    if pg_dump is None:
        logger.warning("pg_dump no disponible; se entrega volcado JSON.")
        return _json_backup()

    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    # host puede venir en el query string (conexiones por socket Unix)
    db_host = query.get("host", [None])[0] or parsed.hostname or "localhost"
    db_port = query.get("port", [None])[0] or parsed.port or 5432
    db_name = (parsed.path or "/").lstrip("/")
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"energy_monitor_backup_{stamp}.sql"
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    cmd = [
        pg_dump,
        "--no-owner",
        "--no-privileges",
        "-h", db_host,
        "-p", str(db_port),
        "-U", parsed.username or "postgres",
        "-d", db_name,
        "-F", "p",
    ]
    logger.info("Ejecutando pg_dump para backup (base=%s)", db_name)
    proc = subprocess.run(cmd, capture_output=True, env=env, check=False, timeout=120)
    if proc.returncode != 0:
        logger.error("pg_dump falló: %s", proc.stderr.decode(errors="replace")[:500])
        return _json_backup()
    return proc.stdout, filename, "application/sql"


def _json_backup() -> tuple[bytes, str, str]:
    """Volcado JSON de todas las tablas (respaldo de compatibilidad)."""
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"energy_monitor_backup_{stamp}.json"
    payload: dict = {"generated_at": dt.datetime.now(dt.UTC).isoformat(), "tables": {}}
    with engine.connect() as conn:
        inspector = inspect(conn)
        for table in inspector.get_table_names():
            if table.startswith("alembic_") or table.startswith("spatial_ref_sys"):
                continue
            rows = conn.execute(text(f'SELECT * FROM "{table}"'))
            cols = list(rows.keys())
            payload["tables"][table] = [dict(zip(cols, [str(v) for v in row])) for row in rows]
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), filename, "application/json"
