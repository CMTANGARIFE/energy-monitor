"""Cálculo de costos (secciones 20-21 de la especificación).

Reglas:
- daily_cost = daily_kwh × tarifa_aplicable_a_esa_fecha
- Un periodo que atraviesa varias tarifas usa la tarifa correcta CADA día.
- NUNCA: total_kwh × tarifa_actual.
- Días sin tarifa configurada: el costo NO se asume; se marcan y se
  reportan claramente (sin inventar valores).
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.rates import RateRepository
from app.services.formatting import compress_date_ranges


class CostCalculator:
    """Calcula costos día a día usando las tarifas configuradas."""

    def __init__(self, db: Session, date_from: dt.date, date_to: dt.date) -> None:
        self.rates = RateRepository(db).rates_for_period(date_from, date_to)
        # Lista ordenada para búsqueda por día
        self._ordered = sorted(self.rates, key=lambda r: r.start_date)

    def rate_for(self, day: dt.date) -> Decimal | None:
        """Tarifa aplicable a una fecha, o None si no existe configuración."""
        for rate in self._ordered:
            if rate.covers(day):
                return rate.price_per_kwh
        return None

    def cost_for(self, day: dt.date, kwh: float) -> Decimal | None:
        """Costo de un día concreto, o None si no hay tarifa para esa fecha."""
        rate = self.rate_for(day)
        if rate is None:
            return None
        return (Decimal(str(kwh)) * rate).quantize(Decimal("0.01"))

    # ------------------------------------------------------------------
    # Agregaciones
    # ------------------------------------------------------------------
    def total_cost(self, daily: dict[dt.date, float]) -> tuple[Decimal | None, list[dt.date]]:
        """Costo total de un mapa {fecha: kwh_total_del_día}.

        Devuelve (costo_calculable, fechas_sin_tarifa).
        El costo es None únicamente si NINGÚN día pudo calcularse.
        """
        total = Decimal("0.00")
        missing: list[dt.date] = []
        any_cost = False
        for day in sorted(daily):
            kwh = daily[day]
            cost = self.cost_for(day, kwh)
            if cost is None:
                missing.append(day)
            else:
                total += cost
                any_cost = True
        return (total if any_cost else None), missing

    def missing_rate_ranges(self, missing_dates: list[dt.date]) -> list[str]:
        """Rangos legibles de días sin tarifa: '01/03/2026 – 15/03/2026'."""
        return compress_date_ranges(missing_dates)
