"""Dependencias comunes de la API."""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db  # noqa: F401  (re-export)
from app.models import EnergyConsumption
from app.repositories.devices import DeviceRepository


def resolve_period(
    date_from: dt.date | None,
    date_to: dt.date | None,
    device_ids: list[int],
    db: Session,
) -> tuple[dt.date, dt.date]:
    """Resuelve el periodo efectivo.

    Si no se indican fechas se usan los límites de los datos disponibles
    de los dispositivos seleccionados (o los últimos 30 días si no hay datos).
    """
    if date_from is not None and date_to is not None:
        if date_to < date_from:
            date_from, date_to = date_to, date_from
        return date_from, date_to

    cond = EnergyConsumption.device_id.in_(device_ids) if device_ids else True
    min_date = db.execute(select(func.min(EnergyConsumption.date)).where(cond)).scalar()
    max_date = db.execute(select(func.max(EnergyConsumption.date)).where(cond)).scalar()

    today = dt.date.today()
    if min_date is None or max_date is None:
        return today - dt.timedelta(days=29), today
    return min_date, max_date


def parse_device_ids(device_ids: str | None) -> list[int]:
    """Convierte '1,2,3' en [1, 2, 3]. Vacío = [] = todos los dispositivos."""
    if not device_ids:
        return []
    result: list[int] = []
    for part in device_ids.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Lista de dispositivos inválida: '{device_ids}'. "
                       "Use identificadores numéricos separados por coma (ejemplo: 1,2,3).",
            ) from exc
    return result


def default_devices(db: Session, device_ids: list[int]) -> list[int]:
    """Si no se especifican dispositivos, usa todos los activos."""
    if device_ids:
        return device_ids
    return [d.id for d in DeviceRepository(db).list(active_only=True)]
