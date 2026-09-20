"""Consultas de consumo y estadísticas (secciones 22-24, 52-53, 55-56)."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import default_devices, get_db, parse_device_ids, resolve_period
from app.repositories.devices import DeviceRepository
from app.services.errors import NotFoundError
from app.services.stats import StatsService

router = APIRouter(prefix="/consumption", tags=["consumo"])


@router.get("")
def consumption(
    device_ids: str | None = Query(default=None, description="IDs separados por coma. Vacío = activos"),
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    db: Session = Depends(get_db),
):
    """Todo lo necesario para el Dashboard en una llamada:

    - `summary`: resumen del periodo (totales, costos, días con/sin datos).
    - `series`:   consumo diario total (Gráfica A).
    - `per_device`: consumo diario por dispositivo (Gráfica B).
    - `cumulative`: consumo acumulado (Gráfica C).
    - `by_device`: consumo total por dispositivo (Gráfica D).
    Los días sin registro NO se rellenan con cero.
    """
    ids = default_devices(db, parse_device_ids(device_ids))
    if not ids:
        return {"summary": None, "series": [], "per_device": {}, "cumulative": [],
                "by_device": [], "cost_series": []}
    d_from, d_to = resolve_period(date_from, date_to, ids, db)
    stats = StatsService(db)
    summary = stats.period_summary(ids, d_from, d_to)
    per_device = stats.per_device_series(ids, d_from, d_to)
    cumulative = stats.cumulative_series(summary["series"])
    return {
        "summary": _strip_internal(summary),
        "series": [p.model_dump(mode="json") for p in summary["series"]],
        "per_device": per_device,
        "cumulative": cumulative,
        "by_device": [d.model_dump() for d in summary["by_device"]],
        "cost_series": summary["cost_series"],
    }


@router.get("/summary")
def consumption_summary(
    device_ids: str | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    db: Session = Depends(get_db),
):
    """Resumen del periodo (tarjetas del Dashboard)."""
    ids = default_devices(db, parse_device_ids(device_ids))
    if not ids:
        return None
    d_from, d_to = resolve_period(date_from, date_to, ids, db)
    summary = StatsService(db).period_summary(ids, d_from, d_to)
    return _strip_internal(summary)


@router.get("/device/{device_id}")
def consumption_for_device(
    device_id: int,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    db: Session = Depends(get_db),
):
    """Consumo + estadísticas de un dispositivo concreto (página de dispositivo)."""
    device = DeviceRepository(db).get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="El dispositivo indicado no existe.")

    ids = [device_id]
    d_from, d_to = resolve_period(date_from, date_to, ids, db)
    stats = StatsService(db)
    try:
        device_stats = stats.device_stats(device_id, d_from, d_to)
        series = stats.per_device_series(ids, d_from, d_to).get(device_id, [])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"device": {"id": device.id, "name": device.name, "active": device.active,
                       "description": device.description, "image": device.image},
            "stats": device_stats, "series": series}


def _strip_internal(summary: dict) -> dict:
    """Elimina claves internas no serializables del resumen."""
    return {k: v for k, v in summary.items() if k not in ("series", "daily_by_device")}
