"""Fixtures de tests.

Por defecto la suite corre sobre SQLite en memoria (hermética y rápida).
La aplicación en producción usa PostgreSQL; las pruebas de integración
adicionales contra PostgreSQL pueden activarse con PYTEST_USE_PG=1
(ver DEVELOPMENT.md).
"""
from __future__ import annotations

import os

# IMPORTANTE: configurar el entorno ANTES de importar la app
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite://")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.base import Base  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.models import Device  # noqa: E402


@pytest.fixture()
def db():
    """Sesión con esquema limpio por test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    """Cliente HTTP de pruebas (esquema limpio por test)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.main import app
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def make_device(db):
    """Fábrica de dispositivos."""
    def _make(name: str = "PC Principal", active: bool = True) -> Device:
        device = Device(name=name, active=active)
        db.add(device)
        db.commit()
        db.refresh(device)
        return device
    return _make
