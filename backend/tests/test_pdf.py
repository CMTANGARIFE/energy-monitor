"""Tests básicos del informe PDF (sección 48 - PDF).

Cubre: generación exitosa, periodo, dispositivo, presencia del contenido
esperado (el texto se extrae del PDF generado).
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.repositories.devices import DeviceRepository
from app.services.importer import ImportService
from app.services.pdf_report import PDFReportService
from app.services.rates import RateService


def _parse(text: str):
    from app.services.csv_parser import parse_csv
    return parse_csv(text.encode(), "c.csv")


def _setup(db, make_device):
    d1 = make_device("PC Principal")
    d2 = make_device("Nevera")
    ImportService(db).run_import(d1.id, _parse(
        "date,kwh,cost\n"
        "2026/03/29,1.56,0\n"
        "2026/03/30,2.10,0\n"
        "2026/03/31,0.50,0\n"
        "2026/04/01,3.00,0\n"
    ))
    ImportService(db).run_import(d2.id, _parse(
        "date,kwh,cost\n"
        "2026/03/29,1.00,0\n"
        "2026/03/30,1.20,0\n"
        "2026/03/31,1.10,0\n"
        "2026/04/01,0.90,0\n"
    ))
    RateService(db).create(dt.date(2026, 3, 1), dt.date(2026, 3, 31), Decimal("800"))
    return d1, d2


def _extract_text(pdf_bytes: bytes) -> str:
    """Extrae el texto del PDF con pypdf (dependencia de pruebas)."""
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_pdf_generacion_exitosa_multi_dispositivo(db, make_device):
    d1, d2 = _setup(db, make_device)
    pdf = PDFReportService(db).generate(
        dt.date(2026, 3, 1), dt.date(2026, 4, 30), [d1.id, d2.id]
    )
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 5000
    text = _extract_text(pdf)
    assert "ENERGY MONITOR" in text
    assert "Resumen general" in text
    assert "Resumen por dispositivo" in text
    assert "PC Principal" in text
    assert "Nevera" in text
    assert "TOTAL" in text
    assert "Información de tarifas" in text


def test_pdf_con_advertencia_sin_tarifa(db, make_device):
    d1, _ = _setup(db, make_device)
    # El periodo incluye 01/04 pero la tarifa termina el 31/03
    pdf = PDFReportService(db).generate(dt.date(2026, 3, 29), dt.date(2026, 4, 2), [d1.id])
    text = _extract_text(pdf)
    assert "ADVERTENCIA" in text
    assert "sin tarifa" in text


def test_pdf_un_solo_dispositivo(db, make_device):
    d1, d2 = _setup(db, make_device)
    pdf = PDFReportService(db).generate(
        dt.date(2026, 3, 29), dt.date(2026, 3, 31), [d2.id]
    )
    text = _extract_text(pdf)
    assert "Nevera" in text
    assert "PC Principal" not in text


def test_pdf_todos_los_dispositivos(db, make_device):
    _setup(db, make_device)
    repo = DeviceRepository(db)
    all_ids = [d.id for d in repo.list()]
    pdf = PDFReportService(db).generate(dt.date(2026, 3, 1), dt.date(2026, 4, 30), all_ids)
    text = _extract_text(pdf)
    assert "Nevera" in text and "PC Principal" in text
