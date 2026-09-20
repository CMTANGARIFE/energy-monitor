"""Motor y sesión de SQLAlchemy.

- `engine`: creado a partir de DATABASE_URL (PostgreSQL en producción).
- `get_db`: dependencia FastAPI que entrega una sesión por request.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings


def _build_engine():
    url = settings.database_url
    # SQLite en memoria: una única conexión compartida para que todas las
    # sesiones vean el mismo esquema (usado en tests y herramientas).
    if url in ("sqlite://", "sqlite+pysqlite://", "sqlite:///:memory:"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    # PostgreSQL/producción: pre_ping evita conexiones muertas tras reinicios
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, future=True)


engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Entrega una sesión de base de datos por request y siempre la cierra."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
