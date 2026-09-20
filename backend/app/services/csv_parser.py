"""Parser y validador de CSV de consumo.

Estructura esperada (secciones 7-11 de la especificación):

    date,kwh,cost
    2026/03/15,0,0
    2026/03/24,2.34,0
    total,8.57,0.00        <- fila "total": se IGNORA completamente
    ...

Reglas implementadas:
- Encabezados: deben existir `date` y `kwh` (comparación insensible a
  mayúsculas y espacios). La columna `cost` se IGNORA por diseño.
- Filas `total` (en la posición de la fecha): ignoradas y contabilizadas.
- Formato de fecha estricto: YYYY/MM/DD (se convierte a DATE, sin hora).
- kwh: numérico, NO negativo; NaN/infinito rechazados.
- kwh = 0 es un dato VÁLIDO y se almacena.
- Errores por fila: número de fila, valor problemático y motivo —
  nunca se ocultan silenciosamente.
- Fechas duplicadas DENTRO del mismo CSV: error bloqueante (no se elige
  una arbitrariamente).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import math
from dataclasses import dataclass, field

DATE_FORMAT = "%Y/%m/%d"
TOTAL_MARKER = "total"


@dataclass
class CsvRowError:
    row: int          # número de fila real en el archivo (encabezado = fila 1)
    field: str
    value: str
    message: str

    def as_dict(self) -> dict:
        return {"row": self.row, "field": self.field, "value": self.value, "message": self.message}


@dataclass
class DailyRecord:
    row: int
    date: dt.date
    kwh: float


@dataclass
class ParsedCSV:
    records: list[DailyRecord] = field(default_factory=list)
    ignored_total_rows: int = 0
    errors: list[CsvRowError] = field(default_factory=list)
    skipped_empty_rows: int = 0
    filename: str = ""

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def date_from(self) -> dt.date | None:
        return min((r.date for r in self.records), default=None)

    @property
    def date_to(self) -> dt.date | None:
        return max((r.date for r in self.records), default=None)

    @property
    def total_kwh(self) -> float:
        return sum(r.kwh for r in self.records)

    def error_payload(self) -> list[dict]:
        return [e.as_dict() for e in self.errors]


def decode_bytes(raw: bytes) -> str:
    """Decodifica el archivo tolerando BOM y codificaciones comunes."""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("El archivo no es un CSV de texto válido (no se pudo decodificar).")


def parse_csv(raw: bytes, filename: str = "") -> ParsedCSV:
    """Parsea y valida el CSV. NUNCA lanza por datos inválidos: devuelve errores."""
    parsed = ParsedCSV(filename=filename)
    text = decode_bytes(raw)
    reader = csv.reader(io.StringIO(text))

    # ------------------- Encabezados -------------------
    try:
        header_row = next(reader)
    except StopIteration:
        parsed.errors.append(CsvRowError(1, "archivo", "", "El archivo está vacío."))
        return parsed

    header = [(h or "").strip().lower() for h in header_row]
    if "date" not in header or "kwh" not in header:
        parsed.errors.append(
            CsvRowError(
                row=1,
                field="encabezados",
                value=",".join(header_row),
                message="Encabezados incorrectos. Se requieren las columnas 'date' y 'kwh' "
                        "(la columna 'cost' es opcional y se ignora).",
            )
        )
        return parsed

    date_idx = header.index("date")
    kwh_idx = header.index("kwh")

    # ------------------- Filas de datos -------------------
    seen_dates: dict[dt.date, int] = {}
    duplicate_rows: dict[dt.date, list[int]] = {}

    for raw_fields in reader:
        line_no = reader.line_num
        fields = [(f or "").strip() for f in raw_fields]

        # Fila completamente vacía: ignorar sin ruido
        if not any(fields):
            parsed.skipped_empty_rows += 1
            continue

        date_cell = fields[date_idx] if date_idx < len(fields) else ""
        kwh_cell = fields[kwh_idx] if kwh_idx < len(fields) else ""

        # Fila 'total': NO es un día; ignorar completamente
        if date_cell.lower() == TOTAL_MARKER:
            parsed.ignored_total_rows += 1
            continue

        # Validación de fecha
        try:
            day = dt.datetime.strptime(date_cell, DATE_FORMAT).date()
        except ValueError:
            parsed.errors.append(
                CsvRowError(
                    row=line_no,
                    field="date",
                    value=date_cell,
                    message=f"Fecha inválida: '{date_cell}'. Se requiere el formato YYYY/MM/DD "
                            "(ejemplo: 2026/03/24).",
                )
            )
            continue

        # Validación de kWh
        try:
            kwh_value = float(kwh_cell)
        except ValueError:
            parsed.errors.append(
                CsvRowError(
                    row=line_no,
                    field="kwh",
                    value=kwh_cell,
                    message=f"Valor de kWh inválido: '{kwh_cell}'. Debe ser un número "
                            "(ejemplo: 2.34).",
                )
            )
            continue
        if math.isnan(kwh_value) or math.isinf(kwh_value):
            parsed.errors.append(
                CsvRowError(row=line_no, field="kwh", value=kwh_cell,
                            message=f"Valor de kWh no finito: '{kwh_cell}'.")
            )
            continue
        if kwh_value < 0:
            parsed.errors.append(
                CsvRowError(
                    row=line_no,
                    field="kwh",
                    value=kwh_cell,
                    message=f"Valor de kWh negativo ({kwh_cell}). No se permiten consumos negativos.",
                )
            )
            continue

        # Duplicados dentro del mismo CSV: error bloqueante (sección 12)
        if day in seen_dates:
            duplicate_rows.setdefault(day, [seen_dates[day]]).append(line_no)
            parsed.errors.append(
                CsvRowError(
                    row=line_no,
                    field="date",
                    value=date_cell,
                    message=f"Fecha duplicada dentro del archivo: {day.isoformat()} ya aparece en la "
                            f"fila {seen_dates[day]}. Corrija el archivo: no se elige una fila "
                            "arbitrariamente.",
                )
            )
            continue

        seen_dates[day] = line_no
        parsed.records.append(DailyRecord(row=line_no, date=day, kwh=kwh_value))

    return parsed
