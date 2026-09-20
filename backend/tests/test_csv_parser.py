"""Tests del parser CSV (sección 48 - CSV).

Cubre: CSV válido, filas 'total', múltiples meses, fecha inválida,
kWh inválido, kWh negativo, encabezados incorrectos, duplicados.
"""
from __future__ import annotations

import datetime as dt

from app.services.csv_parser import parse_csv


CSV_OK = """date,kwh,cost
2026/03/15,0,0
2026/03/16,0,0
2026/03/17,0,0
2026/03/24,2.34,0
2026/03/25,1.18,0
total,3.52,0.00
2026/04/01,5.00,0
"""


def test_csv_valido():
    parsed = parse_csv(CSV_OK.encode(), "consumo.csv")
    assert parsed.valid
    assert len(parsed.records) == 6
    assert parsed.ignored_total_rows == 1
    assert parsed.date_from == dt.date(2026, 3, 15)
    assert parsed.date_to == dt.date(2026, 4, 1)
    assert parsed.total_kwh == 0 + 0 + 0 + 2.34 + 1.18 + 5.00


def test_fila_total_ignorada_completamente():
    parsed = parse_csv(CSV_OK.encode(), "c.csv")
    # La fila 'total' no debe almacenarse como registro diario
    fechas = {r.date for r in parsed.records}
    assert dt.date(2026, 3, 15) in fechas
    assert len(fechas) == 6  # solo fechas reales, ninguna derivada de 'total'
    assert parsed.ignored_total_rows == 1
    # El total lo calcula el sistema con las filas diarias
    assert abs(parsed.total_kwh - 8.52) < 1e-9


def test_cero_kwh_es_dato_valido():
    parsed = parse_csv(CSV_OK.encode(), "c.csv")
    zero = [r for r in parsed.records if r.kwh == 0]
    assert len(zero) == 3  # 15, 16 y 17 de marzo


def test_columna_cost_ignorada():
    parsed = parse_csv(CSV_OK.encode(), "c.csv")
    assert parsed.valid  # aunque 'cost' venga con valores, no afecta


def test_multiples_meses_consecutivos():
    rows = ["date,kwh,cost"]
    for day in range(1, 29):
        rows.append(f"2026/02/{day:02d},{day * 0.1:.2f},0")
    for day in range(1, 32):
        rows.append(f"2026/03/{day:02d},{day * 0.1:.2f},0")
    rows.append("total,86.10,0.00")
    parsed = parse_csv("\n".join(rows).encode(), "c.csv")
    assert parsed.valid
    assert len(parsed.records) == 59
    assert parsed.ignored_total_rows == 1


def test_fecha_invalida():
    csv_text = "date,kwh,cost\n2026/03/24,2.34,0\n2026/99/45,1.00,0\n"
    parsed = parse_csv(csv_text.encode(), "c.csv")
    assert not parsed.valid
    assert len(parsed.errors) == 1
    err = parsed.errors[0]
    assert err.row == 3
    assert err.field == "date"
    assert "2026/99/45" in err.value


def test_formato_fecha_incorrecto():
    csv_text = "date,kwh,cost\n24-03-2026,2.34,0\n"
    parsed = parse_csv(csv_text.encode(), "c.csv")
    assert not parsed.valid
    assert "YYYY/MM/DD" in parsed.errors[0].message


def test_kwh_invalido():
    csv_text = "date,kwh,cost\n2026/03/24,abc,0\n"
    parsed = parse_csv(csv_text.encode(), "c.csv")
    assert not parsed.valid
    assert parsed.errors[0].field == "kwh"
    assert parsed.errors[0].row == 2
    assert parsed.errors[0].value == "abc"


def test_kwh_negativo():
    csv_text = "date,kwh,cost\n2026/03/24,-1.5,0\n"
    parsed = parse_csv(csv_text.encode(), "c.csv")
    assert not parsed.valid
    assert "negativo" in parsed.errors[0].message


def test_encabezados_incorrectos():
    csv_text = "fecha,consumo,costo\n2026/03/24,2.34,0\n"
    parsed = parse_csv(csv_text.encode(), "c.csv")
    assert not parsed.valid
    assert "encabezados" in parsed.errors[0].field


def test_duplicados_dentro_del_mismo_csv():
    csv_text = ("date,kwh,cost\n"
                "2026/03/24,2.34,0\n"
                "2026/03/24,4.56,0\n")
    parsed = parse_csv(csv_text.encode(), "c.csv")
    assert not parsed.valid
    assert any("duplicada" in e.message for e in parsed.errors)
    # Solo la primera fila se considera registro; el archivo se rechaza igualmente
    assert len(parsed.records) == 1


def test_archivo_vacio():
    parsed = parse_csv(b"", "c.csv")
    assert not parsed.valid


def test_fila_sin_suficientes_columnas():
    csv_text = "date,kwh,cost\n2026/03/24\n"
    parsed = parse_csv(csv_text.encode(), "c.csv")
    assert not parsed.valid
    assert parsed.errors[0].field == "kwh"
