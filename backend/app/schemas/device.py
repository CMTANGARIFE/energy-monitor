"""Esquemas de dispositivos."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class DeviceBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    image: str | None = Field(default=None, max_length=255)


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    image: str | None = Field(default=None, max_length=255)


class DeviceStatusUpdate(BaseModel):
    active: bool


class DeviceOut(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    active: bool
    created_at: dt.datetime
    updated_at: dt.datetime


class DeviceDetail(DeviceOut):
    """Detalle con resumen de lifetime (primer/último registro, registros)."""

    first_record_date: dt.date | None = None
    last_record_date: dt.date | None = None
    total_records: int = 0
    lifetime_kwh: float | None = None
