"""Modelo EnergyRate: tarifas de energía por periodo (COP/kWh).

Reglas (especificación):
- end_date NULL = vigente indefinidamente.
- Máximo UNA tarifa abierta (end_date NULL).
- Periodos NO solapados. La validación de negocio vive en
  app/services/rates.py y, en PostgreSQL, además se refuerza con una
  restricción EXCLUDE (migración 0002) a nivel de base de datos.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import TimestampMixin


class EnergyRate(TimestampMixin, Base):
    __tablename__ = "energy_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    start_date: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True, index=True)
    # Numeric(14,4): precios COP/kWh con hasta 4 decimales
    price_per_kwh: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    @property
    def is_open(self) -> bool:
        return self.end_date is None

    def covers(self, day: dt.date) -> bool:
        """Indica si la tarifa aplica para una fecha dada."""
        if day < self.start_date:
            return False
        return self.end_date is None or day <= self.end_date

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EnergyRate {self.start_date}→{self.end_date or '∞'} {self.price_per_kwh} COP/kWh>"
