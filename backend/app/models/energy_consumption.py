"""Modelo EnergyConsumption: consumo diario en kWh.

Reglas de integridad (especificación):
- Clave lógica: UNIQUE(device_id, date) -> UPSERT en importación.
- kwh NO negativo (CHECK).
- kwh = 0 es un dato VÁLIDO (día con consumo cero, distinto de "sin registro").
- `date` es DATE puro de PostgreSQL: consumo diario, sin timestamp ni horas.
- Índices para consultas por device_id y por date.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class EnergyConsumption(TimestampMixin, Base):
    __tablename__ = "energy_consumption"
    __table_args__ = (
        UniqueConstraint("device_id", "date", name="uq_consumption_device_date"),
        CheckConstraint("kwh >= 0", name="ck_consumption_kwh_non_negative"),
        # Índice simple por fecha para agregaciones por periodo
        Index("ix_consumption_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"),  # nunca borrar dispositivo con histórico
        nullable=False,
        index=True,
    )
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    # Numeric(12,4): precisión decimal estable para kWh (0.0001 kWh de resolución)
    kwh: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    device = relationship("Device", back_populates="consumptions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EnergyConsumption device={self.device_id} date={self.date} kwh={self.kwh}>"
