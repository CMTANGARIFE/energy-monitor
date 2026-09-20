"""Repositorio de historial de importaciones."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, ImportHistory


class ImportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **fields) -> ImportHistory:
        record = ImportHistory(**fields)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list(self, device_id: int | None = None, limit: int = 100, offset: int = 0) -> list[ImportHistory]:
        stmt = select(ImportHistory).order_by(ImportHistory.imported_at.desc(), ImportHistory.id.desc())
        if device_id is not None:
            stmt = stmt.where(ImportHistory.device_id == device_id)
        stmt = stmt.limit(max(1, min(limit, 500))).offset(max(0, offset))
        return list(self.db.scalars(stmt).all())

    @staticmethod
    def with_device_names(db: Session, records: list[ImportHistory]) -> list[dict]:
        """Convierte registros a dicts incluyendo el nombre del dispositivo."""
        device_ids = {r.device_id for r in records if r.device_id is not None}
        names: dict[int, str] = {}
        if device_ids:
            rows = db.execute(
                select(Device.id, Device.name).where(Device.id.in_(device_ids))
            ).all()
            names = {dev_id: name for dev_id, name in rows}
        result = []
        for r in records:
            result.append({
                "id": r.id,
                "device_id": r.device_id,
                "device_name": names.get(r.device_id) if r.device_id else None,
                "filename": r.filename,
                "imported_at": r.imported_at,
                "records_found": r.records_found,
                "records_inserted": r.records_inserted,
                "records_updated": r.records_updated,
                "records_ignored": r.records_ignored,
                "status": r.status,
                "error_summary": r.error_summary,
            })
        return result
