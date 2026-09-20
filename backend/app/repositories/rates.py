"""Repositorio de tarifas (energy_rates)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import EnergyRate


class RateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, rate_id: int) -> EnergyRate | None:
        return self.db.get(EnergyRate, rate_id)

    def list(self, date_from: dt.date | None = None, date_to: dt.date | None = None) -> list[EnergyRate]:
        stmt = select(EnergyRate).order_by(EnergyRate.start_date)
        if date_from is not None:
            # Solo tarifas vigentes en o después de date_from (solapan el rango)
            stmt = stmt.where(or_(EnergyRate.end_date.is_(None), EnergyRate.end_date >= date_from))
        if date_to is not None:
            stmt = stmt.where(EnergyRate.start_date <= date_to)
        return list(self.db.scalars(stmt).all())

    def find_overlaps(
        self,
        start_date: dt.date,
        end_date: dt.date | None,
        exclude_id: int | None = None,
    ) -> list[EnergyRate]:
        """Tarifas cuyo periodo solapa con [start_date, end_date|∞).

        Dos rangos [a0, a1] y [b0, b1] solapan si:
            a0 <= b1 (o b1 es ∞)  Y  a1 >= b0 (o a1 es ∞)
        """
        conditions = [or_(EnergyRate.end_date.is_(None), EnergyRate.end_date >= start_date)]
        if end_date is not None:
            conditions.append(EnergyRate.start_date <= end_date)
        stmt = select(EnergyRate).where(and_(*conditions))
        if exclude_id is not None:
            stmt = stmt.where(EnergyRate.id != exclude_id)
        return list(self.db.scalars(stmt).all())

    def find_open_rates(self, exclude_id: int | None = None) -> list[EnergyRate]:
        """Tarifas abiertas (end_date NULL). Debe existir como máximo una."""
        stmt = select(EnergyRate).where(EnergyRate.end_date.is_(None))
        if exclude_id is not None:
            stmt = stmt.where(EnergyRate.id != exclude_id)
        return list(self.db.scalars(stmt).all())

    def rates_for_period(self, date_from: dt.date, date_to: dt.date) -> list[EnergyRate]:
        """Tarifas que aplican (total o parcialmente) a un periodo."""
        return self.find_overlaps(date_from, date_to)

    def create(self, **fields) -> EnergyRate:
        rate = EnergyRate(**fields)
        self.db.add(rate)
        self.db.commit()
        self.db.refresh(rate)
        return rate

    def update(self, rate: EnergyRate, **fields) -> EnergyRate:
        for key, value in fields.items():
            setattr(rate, key, value)
        self.db.commit()
        self.db.refresh(rate)
        return rate

    def delete(self, rate: EnergyRate) -> None:
        self.db.delete(rate)
        self.db.commit()
