"""Pruebas de integración de la API (end-to-end vía HTTP).

Cubre dispositivos CRUD, importación preview/import, consumo, tarifas,
health e informe PDF.
"""
from __future__ import annotations

import datetime as dt

CSV_OK = (
    "date,kwh,cost\n"
    "2026/03/24,2.34,0\n"
    "2026/03/25,1.18,0\n"
    "2026/03/26,0,0\n"
    "total,3.52,0.00\n"
)


# ----------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------
def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


# ----------------------------------------------------------------------
# Dispositivos
# ----------------------------------------------------------------------
def test_crear_y_listar_dispositivo(client):
    resp = client.post("/api/devices", json={"name": "PC Principal", "description": "Equipo de trabajo"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "PC Principal"
    assert body["active"] is True

    resp = client.get("/api/devices")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_nombre_duplicado_rechazado(client):
    client.post("/api/devices", json={"name": "Servidor"})
    resp = client.post("/api/devices", json={"name": "servidor"})
    assert resp.status_code == 409


def test_editar_dispositivo(client):
    created = client.post("/api/devices", json={"name": "TV"}).json()
    resp = client.put(f"/api/devices/{created['id']}", json={"name": "TV Sala", "description": "Sala"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "TV Sala"


def test_desactivar_dispositivo(client):
    created = client.post("/api/devices", json={"name": "Consola"}).json()
    resp = client.patch(f"/api/devices/{created['id']}/status", json={"active": False})
    assert resp.status_code == 200
    assert resp.json()["active"] is False
    # No existe DELETE físico
    assert client.delete(f"/api/devices/{created['id']}").status_code == 405


# ----------------------------------------------------------------------
# Importación
# ----------------------------------------------------------------------
def test_preview_e_importacion_completa(client):
    device = client.post("/api/devices", json={"name": "PC"}).json()

    # Preview: no escribe nada
    resp = client.post(
        "/api/import/preview",
        data={"device_id": device["id"]},
        files={"file": ("marzo.csv", CSV_OK.encode(), "text/csv")},
    )
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["records_found"] == 3
    assert preview["new_records"] == 3
    assert preview["existing_records"] == 0
    assert preview["ignored_rows"] == 1
    assert preview["valid"] is True

    # Importar
    resp = client.post(
        "/api/import",
        data={"device_id": device["id"]},
        files={"file": ("marzo.csv", CSV_OK.encode(), "text/csv")},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["records_inserted"] == 3
    assert result["records_updated"] == 0
    assert result["records_ignored"] == 1

    # Reimportar con un valor cambiado -> UPSERT
    csv_updated = "date,kwh,cost\n2026/03/24,5.00,0\n2026/03/27,3.00,0\n"
    resp = client.post(
        "/api/import",
        data={"device_id": device["id"]},
        files={"file": ("marzo2.csv", csv_updated.encode(), "text/csv")},
    )
    result = resp.json()
    assert result["records_updated"] == 1
    assert result["records_inserted"] == 1

    # Historial de importaciones
    resp = client.get("/api/imports")
    history = resp.json()
    assert len(history) == 2
    assert history[0]["device_name"] == "PC"


def test_importacion_con_errores_devuelve_detalle(client):
    device = client.post("/api/devices", json={"name": "PC"}).json()
    bad_csv = "date,kwh,cost\n2026/03/24,2.34,0\n2026/99/45,1.00,0\n"
    resp = client.post(
        "/api/import",
        data={"device_id": device["id"]},
        files={"file": ("mal.csv", bad_csv.encode(), "text/csv")},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "No se pudo importar" in body["detail"]
    assert any("2026/99/45" in (e.get("value") or "") for e in body["errors"])


def test_importacion_archivo_no_csv_rechazada(client):
    device = client.post("/api/devices", json={"name": "PC"}).json()
    resp = client.post(
        "/api/import",
        data={"device_id": device["id"]},
        files={"file": ("foto.png", b"\x89PNG...", "image/png")},
    )
    assert resp.status_code == 422


# ----------------------------------------------------------------------
# Tarifas
# ----------------------------------------------------------------------
def test_crud_tarifas_con_validaciones(client):
    resp = client.post("/api/rates", json={
        "start_date": "2026-03-01", "end_date": "2026-03-31", "price_per_kwh": "800"
    })
    assert resp.status_code == 201
    rate_id = resp.json()["id"]

    # Solapamiento rechazado
    resp = client.post("/api/rates", json={
        "start_date": "2026-03-15", "end_date": "2026-04-30", "price_per_kwh": "850"
    })
    assert resp.status_code == 409

    # Tarifa adyacente permitida
    resp = client.post("/api/rates", json={
        "start_date": "2026-04-01", "end_date": None, "price_per_kwh": "850"
    })
    assert resp.status_code == 201

    # Segunda tarifa abierta rechazada
    resp = client.post("/api/rates", json={
        "start_date": "2026-05-01", "end_date": None, "price_per_kwh": "900"
    })
    assert resp.status_code == 409

    # Actualizar
    resp = client.put(f"/api/rates/{rate_id}", json={"price_per_kwh": "820"})
    assert resp.status_code == 200
    assert resp.json()["price_per_kwh"] == "820.0000"

    # Eliminar
    resp = client.delete(f"/api/rates/{rate_id}")
    assert resp.status_code == 204


# ----------------------------------------------------------------------
# Consumo y dashboard
# ----------------------------------------------------------------------
def _setup_datos(client):
    device = client.post("/api/devices", json={"name": "PC"}).json()
    client.post("/api/import", data={"device_id": device["id"]},
                files={"file": ("c.csv", CSV_OK.encode(), "text/csv")})
    client.post("/api/rates", json={
        "start_date": "2026-01-01", "end_date": None, "price_per_kwh": "800"})
    return device


def test_consumption_endpoint_dashboard(client):
    device = _setup_datos(client)
    resp = client.get(
        "/api/consumption",
        params={"device_ids": str(device["id"]), "date_from": "2026-03-01",
                "date_to": "2026-03-31"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_kwh"] == 3.52
    assert body["summary"]["total_cost"] == 2816.0   # 3.52 × 800
    assert body["summary"]["days_with_data"] == 3
    assert body["summary"]["days_without_data"] == 28
    assert len(body["series"]) == 3                   # solo días con registro
    assert len(body["cumulative"]) == 3
    assert body["cumulative"][-1]["kwh"] == 3.52
    assert len(body["by_device"]) == 1


def test_consumo_sin_tarifa_marcado(client):
    device = client.post("/api/devices", json={"name": "PC"}).json()
    client.post("/api/import", data={"device_id": device["id"]},
                files={"file": ("c.csv", CSV_OK.encode(), "text/csv")})
    # SIN tarifas configuradas
    resp = client.get(
        "/api/consumption/summary",
        params={"device_ids": str(device["id"]), "date_from": "2026-03-01",
                "date_to": "2026-03-31"},
    )
    body = resp.json()
    assert body["total_cost"] is None
    assert body["days_without_rate"] == 3
    assert body["missing_rate_ranges"]


def test_detalle_dispositivo(client):
    device = _setup_datos(client)
    resp = client.get(f"/api/consumption/device/{device['id']}",
                      params={"date_from": "2026-03-01", "date_to": "2026-03-31"})
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["total_kwh"] == 3.52
    assert stats["estimated_cost"] == 2816.0
    assert stats["first_recorded_day"] == "2026-03-24"


# ----------------------------------------------------------------------
# PDF
# ----------------------------------------------------------------------
def test_generar_pdf(client):
    _setup_datos(client)
    resp = client.post("/api/reports/pdf", json={
        "date_from": "2026-03-01", "date_to": "2026-03-31", "device_ids": None,
    })
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    content = resp.content
    assert content[:5] == b"%PDF-"
    assert len(content) > 3000  # PDF con contenido y gráficas


def test_pdf_periodo_invalido(client):
    resp = client.post("/api/reports/pdf", json={
        "date_from": "2026-03-31", "date_to": "2026-03-01", "device_ids": None,
    })
    assert resp.status_code == 422


# ----------------------------------------------------------------------
# Configuración / backup
# ----------------------------------------------------------------------
def test_settings_info(client):
    resp = client.get("/api/settings/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["currency"] == "COP"


def test_backup_download(client):
    _setup_datos(client)
    resp = client.get("/api/backup")
    assert resp.status_code == 200
    # En tests (SQLite) se entrega volcado JSON de compatibilidad
    assert resp.headers["content-type"].startswith("application/json")
    assert b"devices" in resp.content
