"""Servicio de tarifas: reglas de negocio (secciones 18-21 de la especificación).

- No se permiten periodos solapados.
- Máximo UNA tarifa abierta (end_date NULL = vigente indefinidamente).
- end_date debe ser posterior o igual a start_date.
- price_per_kwh > 0.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.rates import RateRepository
from app.services.errors import ConflictError, NotFoundError, ValidationError
from app.services.formatting import format_date_es


class RateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RateRepository(db)

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------
    def validate_period(self, start_date: dt.date, end_date: dt.date | None) -> None:
        if end_date is not None and end_date < start_date:
            raise ValidationError(
                "La fecha final no puede ser anterior a la fecha inicial "
                f"({format_date_es(end_date)} < {format_date_es(start_date)})."
            )

    def ensure_no_overlap(
        self,
        start_date: dt.date,
        end_date: dt.date | None,
        exclude_id: int | None = None,
    ) -> None:
        overlaps = self.repo.find_overlaps(start_date, end_date, exclude_id=exclude_id)
        if overlaps:
            detail = "; ".join(
                f"{format_date_es(r.start_date)} – "
                f"{format_date_es(r.end_date) if r.end_date else 'vigente'} "
                f"({r.price_per_kwh} COP/kWh)"
                for r in overlaps[:5]
            )
            raise ConflictError(
                "El periodo de la tarifa se solapa con una tarifa existente. "
                f"Periodos en conflicto: {detail}."
            )
        if end_date is None:
            open_rates = self.repo.find_open_rates(exclude_id=exclude_id)
            if open_rates:
                r = open_rates[0]
                raise ConflictError(
                    "Ya existe una tarifa vigente indefinidamente (desde "
                    f"{format_date_es(r.start_date)}, {r.price_per_kwh} COP/kWh). "
                    "Solo puede existir una tarifa abierta: asigne una fecha final a la "
                    "tarifa existente antes de crear otra."
                )

    # ------------------------------------------------------------------
    # CRUD con reglas aplicadas
    # ------------------------------------------------------------------
    def create(self, start_date: dt.date, end_date: dt.date | None, price_per_kwh: Decimal):
        self.validate_period(start_date, end_date)
        self.ensure_no_overlap(start_date, end_date)
        return self.repo.create(
            start_date=start_date, end_date=end_date, price_per_kwh=price_per_kwh
        )

    def update(self, rate_id: int, fields: dict):
        rate = self.repo.get(rate_id)
        if rate is None:
            raise NotFoundError("La tarifa indicada no existe.")
        new_start = fields.get("start_date", rate.start_date)
        new_end = fields.get("end_date", rate.end_date)
        # Permitir borrar explícitamente end_date (vigencia indefinida)
        if "end_date" in fields and fields["end_date"] is None:
            new_end = None
        self.validate_period(new_start, new_end)
        self.ensure_no_overlap(new_start, new_end, exclude_id=rate_id)
        return self.repo.update(
            rate,
            start_date=new_start,
            end_date=new_end,
            price_per_kwh=fields.get("price_per_kwh", rate.price_per_kwh),
        )

    def delete(self, rate_id: int) -> None:
        rate = self.repo.get(rate_id)
        if rate is None:
            raise NotFoundError("La tarifa indicada no existe.")
        self.repo.delete(rate)

    # ------------------------------------------------------------------
    # Consulta de tarifa aplicable
    # ------------------------------------------------------------------
    def rate_for_date(self, day: dt.date):
        for rate in self.repo.rates_for_period(day, day):
            if rate.covers(day):
                return rate
        return None
