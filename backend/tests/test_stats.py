"""Tests de estadísticas (sección 48 - Estadísticas).

Cubre: total, promedio, mínimo, máximo, agregación por dispositivos,
días con/sin datos, serie acumulada.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.services.importer import ImportService
from app.services.rates import RateService
from app.services.stats import StatsService


CSV_MULTIDIA = """date,kwh,cost
2026/03/01,2.00,0
2026/03/02,4.00,0
2026/03/03,1.00,0
2026/03/04,3.00,0
"""


def _import(device_id: int, text: str, db):
    return ImportService(db).run_import(device_id, parse(text))


def parse(text: str):
    from app.services.csv_parser import parse_csv
    return parse_csv(text.encode(), "c.csv")


def test_estadisticas_basicas(db, make_device):
    device = make_device("PC")
    _import(device.id, CSV_MULTIDIA, db)
    stats = StatsService(db).device_stats(
        device.id, dt.date(2026, 3, 1), dt.date(2026, 3, 31)
    )
    assert stats["total_kwh"] == 10.0
    assert stats["avg_daily_kwh"] == 2.5
    assert stats["max_daily_kwh"] == 4.0
    assert stats["max_daily_date"] == dt.date(2026, 3, 2)
    assert stats["min_daily_kwh"] == 1.0
    assert stats["min_daily_date"] == dt.date(2026, 3, 3)
    assert stats["first_recorded_day"] == dt.date(2026, 3, 1)
    assert stats["last_recorded_day"] == dt.date(2026, 3, 4)
    assert stats["days_with_data"] == 4
    assert stats["days_without_data"] == 27


def test_agregacion_por_dispositivos(db, make_device):
    d1 = make_device("PC")
    d2 = make_device("Nevera")
    _import(d1.id, CSV_MULTIDIA, db)
    _import(d2.id, "date,kwh,cost\n2026/03/01,1.50,0\n2026/03/02,0.50,0\n", db)

    summary = StatsService(db).period_summary(
        [d1.id, d2.id], dt.date(2026, 3, 1), dt.date(2026, 3, 31)
    )
    assert summary["total_kwh"] == 12.0
    assert summary["devices_count"] == 2
    by_id = {d.device_id: d for d in summary["by_device"]}
    assert by_id[d1.id].kwh == 10.0
    assert by_id[d2.id].kwh == 2.0
    # Día 01: 2.00 + 1.50 = 3.50
    day1 = next(p for p in summary["series"] if p.date == dt.date(2026, 3, 1))
    assert day1.total == 3.5
    assert day1.values[str(d1.id)] == 2.0
    assert day1.values[str(d2.id)] == 1.5


def test_dia_sin_registro_no_es_cero(db, make_device):
    """Si un dispositivo no tiene registro en una fecha, NO se asume 0."""
    d1 = make_device("PC")
    d2 = make_device("TV")
    _import(d1.id, CSV_MULTIDIA, db)  # PC tiene 4 días
    _import(d2.id, "date,kwh,cost\n2026/03/01,1.00,0\n", db)  # TV solo día 1

    summary = StatsService(db).period_summary(
        [d1.id, d2.id], dt.date(2026, 3, 1), dt.date(2026, 3, 31)
    )
    day2 = next(p for p in summary["series"] if p.date == dt.date(2026, 3, 2))
    assert str(d2.id) not in day2.values  # TV sin dato el 02/03
    assert day2.total == 4.0  # solo el consumo de PC


def test_serie_acumulada(db, make_device):
    device = make_device("PC")
    _import(device.id, CSV_MULTIDIA, db)
    summary = StatsService(db).period_summary([device.id], dt.date(2026, 3, 1), dt.date(2026, 3, 31))
    cumulative = StatsService.cumulative_series(summary["series"])
    values = [c["kwh"] for c in cumulative]
    assert values == [2.0, 6.0, 7.0, 10.0]


def test_costo_en_estadisticas(db, make_device):
    device = make_device("PC")
    _import(device.id, CSV_MULTIDIA, db)
    RateService(db).create(dt.date(2026, 3, 1), dt.date(2026, 3, 31), Decimal("800"))
    stats = StatsService(db).device_stats(device.id, dt.date(2026, 3, 1), dt.date(2026, 3, 31))
    assert stats["estimated_cost"] == 8000.0  # 10 kWh × 800
    assert not stats["cost_incomplete"]


def test_costo_incompleto_por_tarifa_faltante(db, make_device):
    device = make_device("PC")
    _import(device.id, CSV_MULTIDIA, db)
    # Solo tarifa desde el 02/03: el día 01/03 queda sin tarifa
    RateService(db).create(dt.date(2026, 3, 2), dt.date(2026, 3, 31), Decimal("800"))
    stats = StatsService(db).device_stats(device.id, dt.date(2026, 3, 1), dt.date(2026, 3, 31))
    assert stats["estimated_cost"] == 6400.0  # 8 kWh con tarifa (día 1 excluido)
    assert stats["cost_incomplete"] is True
    assert stats["days_without_rate"] == 1
