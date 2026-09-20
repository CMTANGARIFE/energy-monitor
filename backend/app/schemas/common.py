"""Esquemas comunes."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Detalle de un error de validación de datos (fila de CSV, etc.)."""

    row: int | None = None
    field: str | None = None
    value: str | None = None
    message: str


class Message(BaseModel):
    detail: str


class PeriodInfo(BaseModel):
    date_from: dt.date
    date_to: dt.date
    days: int
