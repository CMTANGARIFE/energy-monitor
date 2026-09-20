"""Tests del importador UPSERT (sección 48 - UPSERT).

Cubre: inserción nueva, actualización existente, combinación,
ausencia de duplicados, historial, cero válido.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from app.models import EnergyConsumption, ImportHistory
from app.services.csv_parser import parse_csv
from app.services.errors import ValidationError
from app.services.importer import ImportService


def _parse(text: str, name: str = "c.csv"):
    return parse_csv(text.encode(), name)


def _rows(db, device_id):
    return {
        (r.date, float(r.kwh))
        for r in db.scalars(
            select(EnergyConsumption).where(EnergyConsumption.device_id == device_id)
        ).all()
    }


def test_insercion_nueva(db, make_device):
    device = make_device("Servidor")
    parsed = _parse("date,kwh,cost\n2026/03/24,2.34,0\n2026/03/25,1.18,0\n")
    result = ImportService(db).run_import(device.id, parsed)
    assert result["records_inserted"] == 2
    assert result["records_updated"] == 0
    rows = _rows(db, device.id)
    assert (dt.date(2026, 3, 24), 2.34) in rows
    assert (dt.date(2026, 3, 25), 1.18) in rows


def test_actualizacion_existente_upsert(db, make_device):
    device = make_device("Servidor")
    ImportService(db).run_import(
        device.id,
        _parse("date,kwh,cost\n2026/03/24,2.34,0\n2026/03/25,1.18,0\n"),
    )
    # Reimportar la misma fecha con valor distinto -> UPDATE
    result = ImportService(db).run_import(
        device.id,
        _parse("date,kwh,cost\n2026/03/24,5.00,0\n"),
    )
    assert result["records_updated"] == 1
    assert result["records_inserted"] == 0
    rows = _rows(db, device.id)
    assert (dt.date(2026, 3, 24), 5.00) in rows
    assert (dt.date(2026, 3, 25), 1.18) in rows  # el otro se conserva


def test_combinacion_nuevos_y_existentes(db, make_device):
    """Ejemplo exacto de la especificación (sección 13)."""
    device = make_device("Servidor")
    ImportService(db).run_import(
        device.id,
        _parse("date,kwh,cost\n2026/03/24,2.34,0\n2026/03/25,1.18,0\n2026/03/26,0,0\n"),
    )
    result = ImportService(db).run_import(
        device.id,
        _parse("date,kwh,cost\n2026/03/24,5.00,0\n2026/03/27,3.00,0\n"),
    )
    assert result["records_updated"] == 1   # 2026-03-24
    assert result["records_inserted"] == 1  # 2026-03-27
    rows = _rows(db, device.id)
    assert (dt.date(2026, 3, 24), 5.00) in rows   # actualizado
    assert (dt.date(2026, 3, 25), 1.18) in rows
    assert (dt.date(2026, 3, 26), 0.00) in rows   # cero es dato válido
    assert (dt.date(2026, 3, 27), 3.00) in rows   # nuevo
    assert len(rows) == 4


def test_no_se_crea_duplicado_dispositivo_fecha(db, make_device):
    device = make_device("Servidor")
    service = ImportService(db)
    service.run_import(device.id, _parse("date,kwh,cost\n2026/03/24,2.34,0\n"))
    service.run_import(device.id, _parse("date,kwh,cost\n2026/03/24,9.99,0\n"))
    rows = _rows(db, device.id)
    assert len(rows) == 1
    assert rows == {(dt.date(2026, 3, 24), 9.99)}


def test_cero_kwh_se_almacena(db, make_device):
    device = make_device("Nevera")
    ImportService(db).run_import(device.id, _parse("date,kwh,cost\n2026/03/15,0,0\n"))
    rows = _rows(db, device.id)
    assert (dt.date(2026, 3, 15), 0.0) in rows  # NO se trata como faltante


def test_importacion_con_errores_no_guarda_nada(db, make_device):
    device = make_device("Servidor")
    with pytest.raises(ValidationError) as exc_info:
        ImportService(db).run_import(
            device.id,
            _parse("date,kwh,cost\n2026/03/24,2.34,0\n2026/99/45,1.00,0\n"),
        )
    assert exc_info.value.errors
    assert _rows(db, device.id) == set()  # transaccional: nada persistido
    # La auditoría registra el intento fallido
    history = db.scalars(select(ImportHistory)).all()
    assert len(history) == 1
    assert history[0].status == "error"


def test_filas_total_ignoradas_y_historial(db, make_device):
    device = make_device("Servidor")
    parsed = _parse("date,kwh,cost\n2026/03/24,2.34,0\ntotal,2.34,0.00\n")
    result = ImportService(db).run_import(device.id, parsed)
    assert result["records_ignored"] == 1
    history = db.scalars(select(ImportHistory)).all()
    assert len(history) == 1
    assert history[0].filename == "c.csv"
    assert history[0].records_found == 1
    assert history[0].records_ignored == 1
    assert history[0].status == "success"


def test_preview_no_escribe_bd(db, make_device):
    device = make_device("Servidor")
    ImportService(db).run_import(device.id, _parse("date,kwh,cost\n2026/03/24,2.34,0\n"))
    parsed = _parse("date,kwh,cost\n2026/03/24,9.00,0\n2026/03/28,3.49,0\ntotal,12.49,0\n")
    preview = ImportService(db).preview(device.id, parsed)
    assert preview["records_found"] == 2
    assert preview["new_records"] == 1
    assert preview["existing_records"] == 1
    assert preview["ignored_rows"] == 1
    assert preview["valid"] is True
    # La BD no cambió
    assert _rows(db, device.id) == {(dt.date(2026, 3, 24), 2.34)}


def test_kwh_decimales_preciso(db, make_device):
    device = make_device("TV")
    ImportService(db).run_import(device.id, _parse("date,kwh,cost\n2026/03/24,2.34,0\n"))
    rows = _rows(db, device.id)
    assert next(kwh for (_, kwh) in rows) == 2.34
