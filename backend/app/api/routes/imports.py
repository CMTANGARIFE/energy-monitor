"""Importación de CSV (secciones 14-15): preview, importación e historial.

Seguridad (sección 38):
- Solo se aceptan archivos de texto/CSV, con límite de tamaño configurable.
- El contenido NUNCA se ejecuta; solo se parsea con la librería csv.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.repositories.imports import ImportRepository
from app.services.csv_parser import parse_csv
from app.services.importer import ImportService

logger = logging.getLogger("energy_monitor.api.import")
router = APIRouter(tags=["importación"])


def _read_upload(file: UploadFile) -> tuple[bytes, str]:
    """Lee el archivo subido validando tamaño y extensión básica."""
    filename = file.filename or "consumo.csv"
    if not filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo debe ser un CSV (.csv). Formatos binarios no están permitidos.",
        )
    raw = file.file.read(settings.max_csv_size_bytes + 1)
    if len(raw) > settings.max_csv_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el tamaño máximo permitido "
                   f"({settings.max_csv_size_mb:.0f} MB).",
        )
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo está vacío.",
        )
    return raw, filename


@router.post("/import/preview", response_model=None)
def import_preview(
    file: UploadFile = File(...),
    device_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Paso 2-3 del flujo: analiza el CSV y devuelve la vista previa SIN guardar nada.

    Muestra registros encontrados, nuevos, existentes (serán actualizados),
    filas 'total' ignoradas y errores de validación por fila si los hay.
    """
    raw, filename = _read_upload(file)
    parsed = parse_csv(raw, filename=filename)
    service = ImportService(db)
    return service.preview(device_id, parsed)


@router.post("/import")
def import_consumption(
    file: UploadFile = File(...),
    device_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Paso 4-5: importa el CSV con comportamiento UPSERT (transaccional).

    - Registros nuevos -> INSERT
    - Registros existentes (device_id + date) -> UPDATE del kwh
    - Filas 'total' -> ignoradas
    - Si hay errores de validación: NO se guarda nada (422 con detalle por fila).
    """
    raw, filename = _read_upload(file)
    logger.info("Inicio de importación: archivo=%s dispositivo=%s", filename, device_id)
    parsed = parse_csv(raw, filename=filename)
    service = ImportService(db)
    result = service.run_import(device_id, parsed)
    return result


@router.get("/imports")
def list_imports(
    device_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Historial de importaciones (auditoría y diagnóstico)."""
    records = ImportRepository(db).list(device_id=device_id, limit=limit, offset=offset)
    return ImportRepository.with_device_names(db, records)
