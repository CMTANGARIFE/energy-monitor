# Referencia de la API REST

Base URL (en Docker): `http://<host>:8080/api` — nginx proxya `/api/*` al backend.
Documentación interactiva: `http://<host>:8080/api/docs`… (Swagger en el backend directo:
`http://backend:8000/docs` interno, o expón el 8000 si lo necesitas).

Formato de errores (mensajes claros para el usuario):

```json
{ "detail": "Descripción legible del problema",
  "errors": [ { "row": 37, "field": "date", "value": "2026/99/45", "message": "…" } ] }
```

`errors` solo aparece en la importación de CSV con problemas de validación.

---

## Salud

### `GET /health`
Comprueba backend y base de datos.
```json
{ "status": "ok", "database": "ok", "app": "Energy Monitor", "version": "1.0.0" }
```
Códigos: `200` OK · `503` si la BD no responde.

---

## Dispositivos

### `GET /api/devices?active_only=false`
Lista de dispositivos ordenada por nombre. `active_only=true` filtra los activos.

### `POST /api/devices`
```json
{ "name": "PC Principal", "description": "Equipo de trabajo", "image": null }
```
`201` creado · `409` nombre duplicado (insensible a mayúsculas).

### `GET /api/devices/{id}`
Detalle + resumen de histórico (`first_record_date`, `last_record_date`, `total_records`,
`lifetime_kwh`). `404` si no existe.

### `PUT /api/devices/{id}`
Edita nombre/descripción/imagen (campos opcionales). `404` · `409`.

### `PATCH /api/devices/{id}/status`
```json
{ "active": false }
```
Desactivación lógica (nunca se borran dispositivos con histórico). `404`.

> No existe `DELETE` de dispositivos: es una decisión de diseño para preservar el histórico.

---

## Importación de CSV

### `POST /api/import/preview`  (multipart/form-data)
Campos: `file` (CSV), `device_id`. **No escribe nada.** Devuelve:

```json
{
  "filename": "marzo.csv",
  "device_id": 1,
  "device_name": "PC",
  "records_found": 78, "new_records": 72, "existing_records": 6, "ignored_rows": 3,
  "total_kwh": 123.45, "date_from": "2026-03-01", "date_to": "2026-04-30",
  "errors": [], "valid": true
}
```

`errors` incluye por fila: número, valor y motivo. `413` tamaño excedido · `422` no-CSV.

### `POST /api/import`  (multipart/form-data)
Igual entrada que preview. Ejecuta el UPSERT **transaccional**:

```json
{
  "message": "Importación completada.",
  "device_id": 1, "device_name": "PC",
  "records_found": 78, "records_inserted": 72, "records_updated": 6, "records_ignored": 3,
  "total_kwh": 123.45, "date_from": "2026-03-01", "date_to": "2026-04-30"
}
```

`422` con detalle por fila si hay errores de validación (nada se guarda).

### `GET /api/imports?device_id=&limit=50&offset=0`
Historial de importaciones (auditoría), más reciente primero.

---

## Consumo

### `GET /api/consumption?device_ids=1,2&date_from=2026-03-01&date_to=2026-03-31`
Todo lo del Dashboard en una llamada:

```json
{
  "summary": { "total_kwh": 229.5, "total_cost": 183600, "days_with_data": 40,
               "days_without_data": 22, "days_without_rate": 0,
               "missing_rate_ranges": [], "by_device": [ ... ], ... },
  "series":     [ { "date": "2026-03-01", "total": 3.5, "values": { "1": 2.0, "2": 1.5 } } ],
  "per_device": { "1": [ { "date": "2026-03-01", "kwh": 2.0 } ], "2": [ ... ] },
  "cumulative": [ { "date": "2026-03-01", "kwh": 3.5 } ],
  "by_device":  [ { "device_id": 1, "device_name": "PC", "kwh": 125.4, "cost": 100320, ... } ],
  "cost_series":[ { "date": "2026-03-01", "cost": 2800 } ]
}
```

- Sin `date_from/date_to` usa el rango completo de datos disponibles.
- Sin `device_ids` usa todos los dispositivos **activos**.
- **Los días sin registro NO aparecen** (nunca se asume cero).
- `cost: null` en un día = sin tarifa configurada para esa fecha.

### `GET /api/consumption/summary?…`
Solo el resumen (mismos parámetros).

### `GET /api/consumption/device/{id}?date_from=&date_to=`
Detalle de un dispositivo: `{ device, stats, series }` con todas las estadísticas de la
sección 24 de la especificación (total, promedio, máximo/mínimo diario con fecha, costo
estimado, primer/último día, días con/sin datos). `404` si no existe.

---

## Tarifas

### `GET /api/rates?date_from=&date_to=`
Tarifas ordenadas por fecha inicial (filtros opcionales de solapamiento con rango).

### `POST /api/rates`
```json
{ "start_date": "2026-01-01", "end_date": "2026-03-31", "price_per_kwh": "800" }
```
`end_date: null` = vigente indefinidamente. `201` creado.
`409` si solapa con otra tarifa o ya existe una tarifa abierta · `422` fechas incoherentes o precio ≤ 0.

### `PUT /api/rates/{id}`
Actualiza parcialmente; valida solapamientos excluyéndose a sí misma. `404` · `409` · `422`.

### `DELETE /api/rates/{id}`
Elimina la tarifa. `204` · `404`. Los días que dependían de ella quedan sin costo
(se advierte en dashboard/PDF).

---

## Informes

### `POST /api/reports/pdf`
```json
{ "date_from": "2026-03-01", "date_to": "2026-04-30", "device_ids": null }
```
`device_ids: null` = todos los dispositivos; también acepta `[1,3]`.
Devuelve el PDF (`application/pdf`, `Content-Disposition: attachment`).
Incluye resumen general, tabla por dispositivo, 3 gráficas, tarifas usadas y advertencias.

---

## Backup y configuración

### `GET /api/backup`
Descarga el volcado SQL (`pg_dump`) o JSON de compatibilidad.

### `GET /api/settings/info`
```json
{ "app_name": "Energy Monitor", "version": "1.0.0", "currency": "COP",
  "max_csv_size_mb": 10, "database_engine": "postgresql",
  "pdf_logo_available": true, "default_device_image": "default-device.png" }
```

### `GET /api/settings/stats`
Conteos globales: `{ devices, consumption_records, rates, imports }`.
