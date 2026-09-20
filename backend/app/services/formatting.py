"""Utilidades de formato compartidas (backend / PDF).

Formateo monetario para Colombia (es-CO):
- Separador de miles: punto (1.234.567)
- Separador decimal: coma
- Símbolo: $
Diferenciación clara de unidades: kWh (energía) vs COP/kWh (tarifa).
"""
from __future__ import annotations

from decimal import Decimal


def format_thousands(value: float | Decimal | int, decimals: int = 0) -> str:
    """Formatea un número al estilo es-CO: 1.234.567,89"""
    if isinstance(value, Decimal):
        value = float(value)
    text = f"{value:,.{decimals}f}"
    # Convertir estilo en-US (1,234,567.89) a es-CO (1.234.567,89)
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def format_cop(value: float | Decimal | int | None, decimals: int = 0) -> str:
    """Formatea COP: $ 1.234.567"""
    if value is None:
        return "—"
    return f"$ {format_thousands(value, decimals=decimals)}"


def format_kwh(value: float | Decimal | int | None, decimals: int = 2) -> str:
    """Formatea energía: 12,34 kWh"""
    if value is None:
        return "—"
    return f"{format_thousands(value, decimals=decimals)} kWh"


def format_date_es(day) -> str:
    """Formatea fecha como DD/MM/YYYY (formato de informes)."""
    return day.strftime("%d/%m/%Y")


def compress_date_ranges(dates: list) -> list[str]:
    """Comprime fechas consecutivas en rangos legibles.

    Ejemplo: [01/03, 02/03, 03/03, 10/03] -> ["01/03/2026 – 03/03/2026", "10/03/2026"]
    """
    import datetime as dt

    if not dates:
        return []
    ordered = sorted(set(dates))
    ranges: list[tuple[dt.date, dt.date]] = []
    start = prev = ordered[0]
    for day in ordered[1:]:
        if day - prev == dt.timedelta(days=1):
            prev = day
        else:
            ranges.append((start, prev))
            start = prev = day
    ranges.append((start, prev))
    return [
        f"{format_date_es(a)} – {format_date_es(b)}" if a != b else format_date_es(a)
        for a, b in ranges
    ]
