"""Tests de tarifas (sección 48 - Tarifas).

Cubre: tarifa válida, sin fecha final, solapamiento, precio inválido,
cálculo con una tarifa, cálculo atravesando varias tarifas, fecha sin tarifa.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from app.services.costs import CostCalculator
from app.services.errors import ConflictError, ValidationError
from app.services.rates import RateService


# ----------------------------------------------------------------------
# Reglas de creación/validación
# ----------------------------------------------------------------------
def test_tarifa_valida(db):
    rate = RateService(db).create(dt.date(2026, 1, 1), dt.date(2026, 3, 31), Decimal("800"))
    assert rate.price_per_kwh == Decimal("800.0000")


def test_tarifa_sin_fecha_final(db):
    rate = RateService(db).create(dt.date(2026, 7, 1), None, Decimal("900"))
    assert rate.is_open
    assert rate.covers(dt.date(2030, 1, 1))


def test_solapamiento_rechazado(db):
    service = RateService(db)
    service.create(dt.date(2026, 1, 1), dt.date(2026, 6, 30), Decimal("800"))
    with pytest.raises(ConflictError):
        service.create(dt.date(2026, 4, 1), dt.date(2026, 8, 31), Decimal("850"))


def test_solapamiento_con_tarifa_abierta_rechazado(db):
    service = RateService(db)
    service.create(dt.date(2026, 1, 1), None, Decimal("800"))
    with pytest.raises(ConflictError):
        service.create(dt.date(2026, 12, 1), None, Decimal("900"))


def test_maximo_una_tarifa_abierta(db):
    service = RateService(db)
    service.create(dt.date(2026, 1, 1), dt.date(2026, 3, 31), Decimal("800"))
    service.create(dt.date(2026, 7, 1), None, Decimal("900"))
    with pytest.raises(ConflictError):
        service.create(dt.date(2027, 1, 1), None, Decimal("950"))


def test_tarifas_adyacentes_permitidas(db):
    """Ejemplo válido de la especificación: 3 periodos contiguos."""
    service = RateService(db)
    service.create(dt.date(2026, 1, 1), dt.date(2026, 3, 31), Decimal("800"))
    service.create(dt.date(2026, 4, 1), dt.date(2026, 6, 30), Decimal("850"))
    service.create(dt.date(2026, 7, 1), None, Decimal("900"))
    assert len(service.repo.list()) == 3


def test_fecha_final_anterior_rechazada(db):
    with pytest.raises(ValidationError):
        RateService(db).create(dt.date(2026, 6, 1), dt.date(2026, 3, 1), Decimal("800"))


def test_precio_invalido_rechazado():
    from pydantic import ValidationError as PydanticError
    from app.schemas.rate import RateCreate

    with pytest.raises(PydanticError):
        RateCreate(start_date=dt.date(2026, 1, 1), end_date=None, price_per_kwh=Decimal("0"))
    with pytest.raises(PydanticError):
        RateCreate(start_date=dt.date(2026, 1, 1), end_date=None, price_per_kwh=Decimal("-5"))


# ----------------------------------------------------------------------
# Cálculo de costos
# ----------------------------------------------------------------------
def _calc(db) -> CostCalculator:
    return CostCalculator(db, dt.date(2026, 1, 1), dt.date(2026, 12, 31))


def test_calculo_con_una_tarifa(db):
    RateService(db).create(dt.date(2026, 3, 1), dt.date(2026, 3, 31), Decimal("800"))
    cost = _calc(db).cost_for(dt.date(2026, 3, 15), 2.5)
    assert cost == Decimal("2000.00")


def test_calculo_atravesando_varias_tarifas(db):
    """Cada día usa SU tarifa (sección 20): nunca total × tarifa_actual."""
    service = RateService(db)
    service.create(dt.date(2026, 3, 1), dt.date(2026, 3, 31), Decimal("800"))
    service.create(dt.date(2026, 4, 1), dt.date(2026, 4, 30), Decimal("850"))

    calc = _calc(db)
    daily = {dt.date(2026, 3, 31): 10.0, dt.date(2026, 4, 1): 10.0}
    total, missing = calc.total_cost(daily)
    assert total == Decimal("16500.00")  # 10×800 + 10×850
    assert missing == []


def test_fecha_sin_tarifa_no_inventar(db):
    RateService(db).create(dt.date(2026, 4, 1), None, Decimal("850"))
    calc = _calc(db)
    assert calc.cost_for(dt.date(2026, 3, 15), 5.0) is None
    total, missing = calc.total_cost({dt.date(2026, 3, 15): 5.0})
    assert total is None          # nada calculable
    assert missing == [dt.date(2026, 3, 15)]


def test_periodo_con_dias_con_y_sin_tarifa(db):
    RateService(db).create(dt.date(2026, 4, 1), None, Decimal("850"))
    calc = _calc(db)
    daily = {dt.date(2026, 3, 31): 10.0, dt.date(2026, 4, 1): 10.0}
    total, missing = calc.total_cost(daily)
    assert total == Decimal("8500.00")   # solo el día con tarifa
    assert missing == [dt.date(2026, 3, 31)]
    assert calc.missing_rate_ranges(missing) == ["31/03/2026"]


def test_rangos_legibles_sin_tarifa(db):
    RateService(db).create(dt.date(2026, 5, 1), None, Decimal("900"))
    calc = _calc(db)
    daily = {dt.date(2026, 3, 1): 1, dt.date(2026, 3, 2): 1, dt.date(2026, 3, 3): 1,
             dt.date(2026, 3, 10): 1}
    _, missing = calc.total_cost(daily)
    assert calc.missing_rate_ranges(missing) == ["01/03/2026 – 03/03/2026", "10/03/2026"]
