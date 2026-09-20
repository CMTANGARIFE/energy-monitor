"""Esquemas de consumo y estadísticas."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class ConsumptionDailyPoint(BaseModel):
    """Un día de consumo para las gráficas.

    `values` contiene kwh por device_id SOLO de los días con registro real;
    la ausencia de clave significa "día sin dato" (NO se asume cero).
    """

    date: dt.date
    total: float
    values: dict[str, float]  # claves: device_id como string


class ConsumptionDeviceRow(BaseModel):
    """Fila de consumo de un dispositivo específico."""

    date: dt.date
    kwh: float


class DevicePeriodCost(BaseModel):
    device_id: int
    device_name: str
    kwh: float
    cost: float | None = None              # None si ninguna tarifa aplicable
    cost_incomplete: bool = False          # True si faltan días por tarifa ausente
    days_without_rate: int = 0


class ConsumptionSummary(BaseModel):
    """Resumen agregado para Dashboard / informes."""

    date_from: dt.date
    date_to: dt.date
    days: int
    devices_count: int
    total_kwh: float
    avg_daily_kwh: float | None = None     # sobre días CON datos
    max_daily_kwh: float | None = None
    max_daily_date: dt.date | None = None
    min_daily_kwh: float | None = None
    min_daily_date: dt.date | None = None
    first_data_date: dt.date | None = None
    last_data_date: dt.date | None = None
    days_with_data: int
    days_without_data: int
    # Costos (calculados día a día con la tarifa aplicable a cada fecha)
    total_cost: float | None = None
    cost_incomplete: bool = False
    days_without_rate: int = 0
    missing_rate_ranges: list[str] = []    # p. ej. "01/03/2026 – 15/03/2026"
    by_device: list[DevicePeriodCost] = []


class DeviceConsumptionStats(BaseModel):
    """Estadísticas de un dispositivo (sección 24 de la especificación)."""

    device_id: int
    device_name: str
    date_from: dt.date
    date_to: dt.date
    total_kwh: float
    avg_daily_kwh: float | None = None
    max_daily_kwh: float | None = None
    max_daily_date: dt.date | None = None
    min_daily_kwh: float | None = None
    min_daily_date: dt.date | None = None
    estimated_cost: float | None = None
    cost_incomplete: bool = False
    days_without_rate: int = 0
    first_recorded_day: dt.date | None = None
    last_recorded_day: dt.date | None = None
    days_with_data: int
    days_without_data: int
