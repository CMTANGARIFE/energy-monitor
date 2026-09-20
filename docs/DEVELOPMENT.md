# Desarrollo

Guía para trabajar sobre el código: entorno local, tests y convenciones.

## Estructura del backend

```
backend/app/
├── api/            Rutas FastAPI (devices, imports, consumption, rates, reports, backup)
├── models/         Modelos SQLAlchemy (Device, EnergyConsumption, EnergyRate, ImportHistory)
├── schemas/        Esquemas Pydantic de entrada/salida
├── services/       Lógica de negocio:
│   ├── csv_parser.py   parseo + validación de CSV (funciones puras, muy testeable)
│   ├── importer.py     preview + importación UPSERT transaccional
│   ├── rates.py        reglas de tarifas (solapamientos, vigencia)
│   ├── costs.py        cálculo de costos día a día
│   ├── stats.py        estadísticas y agregaciones
│   ├── pdf_report.py   informe PDF (ReportLab + matplotlib)
│   └── backup.py       respaldo (pg_dump / JSON)
├── repositories/   Acceso a datos (consultas SQL del ORM)
├── database/       Motor, sesión y Base declarativa
└── main.py         Fábrica de la app, CORS, manejo de errores
```

Separación clara: **API** (HTTP) → **servicios** (reglas de negocio) →
**repositorios** (datos). La generación de informes vive aparte en servicios.

## Entorno local sin Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/energy_monitor
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 con proxy /api → :8000
```

## Tests

### Backend (pytest)

```bash
cd backend
pytest                      # suite completa
pytest tests/test_csv_parser.py -v    # solo un módulo
```

Por defecto los tests corren sobre **SQLite en memoria** (hermético, sin servicios).
La semántica del UPSERT (`ON CONFLICT (device_id, date) DO UPDATE`) es idéntica en ambos
motores gracias al soporte de dialectos de SQLAlchemy.

**Verificación contra PostgreSQL real** (recomendado antes de releases):

```bash
# Con un PostgreSQL accesible:
export TEST_DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/energy_test
pytest

# O con Docker:
docker compose exec -e TEST_DATABASE_URL=postgresql+psycopg2://energy:CLAVE@postgres:5432/energy_monitor_test backend pytest
```

### Cobertura de la suite

- **CSV** (`test_csv_parser.py`): CSV válido, filas `total`, múltiples meses, fecha
  inválida, formato incorrecto, kWh inválido/negativo, encabezados incorrectos,
  duplicados internos, archivo vacío, filas truncadas.
- **UPSERT** (`test_importer.py`): inserción, actualización, combinación de nuevos +
  existentes (ejemplo exacto de la especificación), ausencia de duplicados, cero
  almacenado, transaccionalidad (nada se guarda si hay errores), historial.
- **Tarifas y costos** (`test_rates.py`): creación válida, tarifa abierta única,
  solapamientos, tarifas adyacentes, fechas incoherentes, precio inválido, cálculo con
  una tarifa, cálculo atravesando varias tarifas, días sin tarifa (no se inventan),
  rangos legibles de días sin tarifa.
- **Estadísticas** (`test_stats.py`): total, promedio, máximo/mínimo con fecha, agregación
  por dispositivos, día sin registro ≠ cero, serie acumulada, costos completos e incompletos.
- **API** (`test_api.py`): endpoints end-to-end (dispositivos CRUD, preview/import,
  historial, tarifas con validaciones, consumo/dashboard, health, settings, backup, PDF).
- **PDF** (`test_pdf.py`): generación, contenido esperado (texto extraído con pypdf),
  advertencias, dispositivo único y todos los dispositivos.

### Frontend (vitest)

```bash
cd frontend
npm run test        # utilidades de formato es-CO y rangos de fecha
npx tsc -b          # chequeo de tipos estricto
npm run build       # build de producción
```

## Convenciones

- **Python**: tipado con anotaciones, `from __future__ import annotations`, docstrings en
  español, logging por módulo (`energy_monitor.import`, `energy_monitor.pdf`, …).
- **Errores de dominio** (`services/errors.py`): `NotFoundError` → 404, `ConflictError` →
  409, `ValidationError` → 422 con detalle por fila. `main.py` los traduce a mensajes
  claros; los trazos completos van al log.
- **TypeScript**: estricto (`strict: true`), sin `any`; componentes funcionales con hooks.
- **Commits sugeridos**: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.

## Añadir una migración

1. Edita los modelos en `app/models/`.
2. `alembic revision --autogenerate -m "mensaje"`
3. Revisa el archivo generado en `migrations/versions/`.
4. `alembic upgrade head` y corre los tests.

## Variables de entorno (backend)

| Variable | Default | Uso |
|----------|---------|-----|
| `DATABASE_URL` | (ver `.env.example`) | Cadena SQLAlchemy de conexión |
| `CORS_ORIGINS` | `*` | Orígenes CORS permitidos (coma-separados) |
| `ASSETS_DIR` | `./assets` | Carpeta de assets del PDF |
| `MAX_CSV_SIZE_MB` | `10` | Límite de tamaño de CSV |
| `FRONTEND_DIST` | (vacío) | Si apunta al build del frontend, se sirve desde FastAPI (modo sin Docker) |
