#!/bin/sh
# Energy Monitor - entrypoint del backend
# Espera a PostgreSQL, aplica migraciones Alembic y arranca la API.

set -e

echo "[entrypoint] Esperando base de datos..."
python - <<'PY'
import os, time, sys
import psycopg2

url = os.environ.get("DATABASE_URL", "")
# Convertir URL de SQLAlchemy a parámetros psycopg2
if url.startswith("postgresql+psycopg2://"):
    url = url.replace("postgresql+psycopg2://", "postgresql://", 1)

for attempt in range(30):
    try:
        conn = psycopg2.connect(url, connect_timeout=3)
        conn.close()
        print("[entrypoint] Base de datos disponible.")
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print(f"[entrypoint] Intento {attempt + 1}/30 sin conexión: {e.__class__.__name__}")
        time.sleep(2)

print("[entrypoint] ERROR: no se pudo conectar a la base de datos.")
sys.exit(1)
PY

echo "[entrypoint] Aplicando migraciones Alembic..."
alembic upgrade head

echo "[entrypoint] Iniciando API..."
exec "$@"
