"""Esquemas de importación CSV."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ErrorDetail


class ImportPreviewRequest(BaseModel):
    device_id: int


class ImportPreview(BaseModel):
    """Vista previa antes de importar (no escribe en la BD)."""

    filename: str
    device_id: int
    device_name: str | None = None
    records_found: int              # filas diarias válidas detectadas
    new_records: int                # no existen en la BD -> INSERT
    existing_records: int           # existen -> serán ACTUALIZADOS (UPSERT)
    ignored_rows: int               # filas "total" ignoradas
    total_kwh: float
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    errors: list[ErrorDetail] = []
    valid: bool                     # False si hay errores bloqueantes


class ImportResult(BaseModel):
    """Resultado posterior a la importación."""

    message: str
    device_id: int
    device_name: str | None = None
    records_found: int
    records_inserted: int
    records_updated: int
    records_ignored: int
    total_kwh: float
    date_from: dt.date | None = None
    date_to: dt.date | None = None


class ImportHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int | None
    device_name: str | None = None
    filename: str
    imported_at: dt.datetime
    records_found: int
    records_inserted: int
    records_updated: int
    records_ignored: int
    status: str
    error_summary: str | None = None
