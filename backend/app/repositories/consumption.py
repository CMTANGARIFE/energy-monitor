"""Repositorio de consumo diario (energy_consumption)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import EnergyConsumption


class ConsumptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # UPSERT (especificación sección 13)
    # Clave: UNIQUE(device_id, date). No existe -> INSERT; existe -> UPDATE kwh.
    # Soporta PostgreSQL (producción) y SQLite (tests) con la misma semántica.
    # ------------------------------------------------------------------
    def upsert_many(self, device_id: int, rows: list[dict]) -> None:
        if not rows:
            return
        payload = [
            {"device_id": device_id, "date": r["date"], "kwh": Decimal(str(r["kwh"])).quantize(Decimal("0.0001"))}
            for r in rows
        ]
        if self.db.bind.dialect.name == "postgresql":
            stmt = pg_insert(EnergyConsumption).values(payload)
            stmt = stmt.on_conflict_do_update(
                index_elements=["device_id", "date"],
                set_={"kwh": stmt.excluded.kwh, "updated_at": func.now()},
            )
        else:  # sqlite (tests / desarrollo ligero)
            stmt = sqlite_insert(EnergyConsumption).values(payload)
            stmt = stmt.on_conflict_do_update(
                index_elements=["device_id", "date"],
                set_={"kwh": stmt.excluded.kwh},
            )
        self.db.execute(stmt)

    def existing_dates(self, device_id: int, dates: list[dt.date]) -> set[dt.date]:
        """Fechas que YA existen en la BD para el dispositivo."""
        if not dates:
            return set()
        unique_dates = list(set(dates))
        stmt = select(EnergyConsumption.date).where(
            EnergyConsumption.device_id == device_id,
            EnergyConsumption.date.in_(unique_dates),
        )
        return set(self.db.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Consultas para gráficas y resúmenes
    # ------------------------------------------------------------------
    def rows_for_period(
        self, device_ids: list[int], date_from: dt.date, date_to: dt.date
    ) -> list[EnergyConsumption]:
        stmt = (
            select(EnergyConsumption)
            .where(
                EnergyConsumption.device_id.in_(device_ids),
                EnergyConsumption.date >= date_from,
                EnergyConsumption.date <= date_to,
            )
            .order_by(EnergyConsumption.date, EnergyConsumption.device_id)
        )
        return list(self.db.scalars(stmt).all())

    def daily_totals_by_device(
        self, device_ids: list[int], date_from: dt.date, date_to: dt.date
    ) -> list[tuple[dt.date, int, Decimal]]:
        """(fecha, device_id, SUM(kwh)) agregado por día y dispositivo."""
        stmt = (
            select(
                EnergyConsumption.date,
                EnergyConsumption.device_id,
                func.sum(EnergyConsumption.kwh).label("kwh"),
            )
            .where(
                EnergyConsumption.device_id.in_(device_ids),
                EnergyConsumption.date >= date_from,
                EnergyConsumption.date <= date_to,
            )
            .group_by(EnergyConsumption.date, EnergyConsumption.device_id)
            .order_by(EnergyConsumption.date)
        )
        return list(self.db.execute(stmt).all())

    def device_totals(
        self, device_ids: list[int], date_from: dt.date, date_to: dt.date
    ) -> list[tuple[int, Decimal]]:
        """SUM(kwh) total por dispositivo en el periodo."""
        stmt = (
            select(EnergyConsumption.device_id, func.sum(EnergyConsumption.kwh).label("kwh"))
            .where(
                EnergyConsumption.device_id.in_(device_ids),
                EnergyConsumption.date >= date_from,
                EnergyConsumption.date <= date_to,
            )
            .group_by(EnergyConsumption.device_id)
        )
        return list(self.db.execute(stmt).all())

    def dates_without_records(
        self, device_ids: list[int], date_from: dt.date, date_to: dt.date
    ) -> set[dt.date]:
        """Días del periodo (por dispositivo) sin ningún registro."""
        if not device_ids:
            return set()
        stmt = select(EnergyConsumption.device_id, EnergyConsumption.date).where(
            EnergyConsumption.device_id.in_(device_ids),
            EnergyConsumption.date >= date_from,
            EnergyConsumption.date <= date_to,
        )
        found = {(dev, d) for dev, d in self.db.execute(stmt).all()}
        missing: set[dt.date] = set()
        for dev in device_ids:
            for day in daterange(date_from, date_to):
                if (dev, day) not in found:
                    missing.add(day)
        return missing


def daterange(date_from: dt.date, date_to: dt.date):
    """Itera día por día un rango inclusive."""
    day = date_from
    while day <= date_to:
        yield day
        day += dt.timedelta(days=1)
