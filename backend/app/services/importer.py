"""Servicio de importación CSV: vista previa + importación UPSERT transaccional.

Flujo (sección 14 de la especificación):
1. preview:  analiza el archivo y compara contra la BD SIN escribir nada.
2. import:   valida todo -> transacción -> INSERT/UPDATE (UPSERT) -> commit.
             Si algo falla críticamente -> rollback y la BD queda intacta.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import Device
from app.repositories.consumption import ConsumptionRepository
from app.repositories.imports import ImportRepository
from app.services.csv_parser import ParsedCSV
from app.services.errors import NotFoundError, ValidationError

logger = logging.getLogger("energy_monitor.import")


class ImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.consumptions = ConsumptionRepository(db)
        self.imports = ImportRepository(db)

    # ------------------------------------------------------------------
    # Vista previa (Paso 3 del flujo) — NO modifica la base de datos
    # ------------------------------------------------------------------
    def preview(self, device_id: int, parsed: ParsedCSV) -> dict:
        device = self._get_device(device_id)
        records = parsed.records
        existing = self.consumptions.existing_dates(device_id, [r.date for r in records])
        new_records = sum(1 for r in records if r.date not in existing)

        preview = {
            "filename": parsed.filename,
            "device_id": device_id,
            "device_name": device.name,
            "records_found": len(records),
            "new_records": new_records,
            "existing_records": len(records) - new_records,
            "ignored_rows": parsed.ignored_total_rows,
            "total_kwh": round(parsed.total_kwh, 4),
            "date_from": parsed.date_from,
            "date_to": parsed.date_to,
            "errors": parsed.error_payload(),
            "valid": parsed.valid,
        }
        logger.info(
            "Preview importación: archivo=%s dispositivo=%s encontrados=%s nuevos=%s "
            "existentes=%s ignorados=%s válido=%s",
            parsed.filename, device.name, len(records), new_records,
            len(records) - new_records, parsed.ignored_total_rows, parsed.valid,
        )
        return preview

    # ------------------------------------------------------------------
    # Importación real (UPSERT transaccional)
    # ------------------------------------------------------------------
    def run_import(self, device_id: int, parsed: ParsedCSV) -> dict:
        device = self._get_device(device_id)

        # 1) Validar TODO antes de tocar la base de datos
        if not parsed.valid:
            summary = f"{len(parsed.errors)} error(es) de validación."
            self._record_history(
                device_id=device_id,
                filename=parsed.filename,
                records_found=len(parsed.records),
                records_inserted=0,
                records_updated=0,
                records_ignored=parsed.ignored_total_rows,
                status="error",
                error_summary=summary,
            )
            raise ValidationError(
                "No se pudo importar el archivo: contiene errores de validación.",
                errors=parsed.error_payload(),
            )

        rows = [{"date": r.date, "kwh": r.kwh} for r in parsed.records]
        existing = self.consumptions.existing_dates(device_id, [r["date"] for r in rows])
        updated_count = sum(1 for r in rows if r["date"] in existing)
        inserted_count = len(rows) - updated_count

        # 2) Transacción: insertar/actualizar + historial -> commit
        try:
            self.consumptions.upsert_many(device_id, rows)
            history = self._record_history(
                device_id=device_id,
                filename=parsed.filename,
                records_found=len(rows),
                records_inserted=inserted_count,
                records_updated=updated_count,
                records_ignored=parsed.ignored_total_rows,
                status="success",
                error_summary=None,
            )
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            self.db.rollback()
            logger.exception("Error crítico durante la importación: %s", exc)
            self._record_history(
                device_id=device_id,
                filename=parsed.filename,
                records_found=len(rows),
                records_inserted=0,
                records_updated=0,
                records_ignored=parsed.ignored_total_rows,
                status="error",
                error_summary=f"Error crítico de base de datos: {exc.__class__.__name__}",
            )
            self.db.commit()
            raise ValidationError(
                "No se pudo importar el archivo por un error de base de datos. "
                "Revise los logs del backend."
            ) from exc

        logger.info(
            "Importación completada: archivo=%s dispositivo=%s nuevos=%s actualizados=%s "
            "ignorados=%s kwh=%.4f",
            parsed.filename, device.name, inserted_count, updated_count,
            parsed.ignored_total_rows, parsed.total_kwh,
        )
        return {
            "message": "Importación completada.",
            "device_id": device_id,
            "device_name": device.name,
            "records_found": len(rows),
            "records_inserted": inserted_count,
            "records_updated": updated_count,
            "records_ignored": parsed.ignored_total_rows,
            "total_kwh": round(parsed.total_kwh, 4),
            "date_from": parsed.date_from,
            "date_to": parsed.date_to,
        }

    # ------------------------------------------------------------------
    def _get_device(self, device_id: int) -> Device:
        device = self.db.get(Device, device_id)
        if device is None:
            raise NotFoundError("El dispositivo seleccionado no existe.")
        return device

    def _record_history(self, **fields):
        return self.imports.create(**fields)
