"""Repositorio de dispositivos."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Device, EnergyConsumption


class DeviceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, device_id: int) -> Device | None:
        return self.db.get(Device, device_id)

    def get_by_name(self, name: str) -> Device | None:
        stmt = select(Device).where(func.lower(Device.name) == name.strip().lower())
        return self.db.scalars(stmt).first()

    def list(self, active_only: bool = False) -> list[Device]:
        stmt = select(Device).order_by(Device.name)
        if active_only:
            stmt = stmt.where(Device.active.is_(True))
        return list(self.db.scalars(stmt).all())

    def create(self, **fields) -> Device:
        device = Device(**fields)
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def update(self, device: Device, **fields) -> Device:
        for key, value in fields.items():
            if value is not None or key in ("description", "image"):
                setattr(device, key, value)
        self.db.commit()
        self.db.refresh(device)
        return device

    def set_status(self, device: Device, active: bool) -> Device:
        device.active = active
        self.db.commit()
        self.db.refresh(device)
        return device

    # --- Resumen de lifetime para el detalle del dispositivo ---
    def lifetime_summary(self, device_id: int) -> dict:
        stmt = select(
            func.count(EnergyConsumption.id),
            func.min(EnergyConsumption.date),
            func.max(EnergyConsumption.date),
            func.coalesce(func.sum(EnergyConsumption.kwh), 0),
        ).where(EnergyConsumption.device_id == device_id)
        row = self.db.execute(stmt).one()
        return {
            "total_records": int(row[0] or 0),
            "first_record_date": row[1],
            "last_record_date": row[2],
            "lifetime_kwh": float(row[3] or 0),
        }
