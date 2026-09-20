# Energy Monitor

Aplicación web **local** para registrar, importar, almacenar, visualizar y analizar el
consumo diario de energía eléctrica de diferentes dispositivos, con cálculo de costos
según tarifas configurables e informes PDF profesionales.

Pensada para ejecutarse en un servidor doméstico con **Docker Compose** y accederse
desde cualquier navegador de la red local.

---

## Características

- **Dispositivos**: crear, editar, activar/desactivar (nunca se borra el histórico),
  imagen personalizable y página de detalle con estadísticas.
- **Importación CSV**: arrastrar y soltar, vista previa antes de importar, detección de
  registros nuevos vs. existentes, **UPSERT** (actualiza si coincide dispositivo + fecha),
  filas `total` ignoradas, columna `cost` ignorada, validación detallada fila por fila e
  historial de importaciones.
- **Consumo**: diario en kWh, con diferencia entre *día con consumo 0* y *día sin registro*.
- **Tarifas**: precio COP/kWh por periodos, sin solapamientos, soporta tarifa vigente
  indefinida. El costo se calcula **día por día** con la tarifa aplicable a cada fecha.
- **Dashboard**: tarjetas de resumen, filtros por fecha (accesos rápidos) y por
  dispositivos, y 5 gráficas (diario total, diario por dispositivo, acumulado,
  por dispositivo y costo diario).
- **Informes PDF**: generados en el backend (ReportLab + gráficas matplotlib) con
  encabezado, logo configurable, tablas, gráficas, tarifas utilizadas, advertencias,
  numeración "Página X de Y" y fecha de generación.
- **Backup**: botón de descarga desde la aplicación + procedimiento documentado con
  `pg_dump`. Los datos persisten en un volumen Docker.
- **Assets reemplazables**: logo, favicon e imagen por defecto se sustituyen sin tocar código.

## Requisitos

- Docker Engine 24+ con Docker Compose v2 (`docker compose`)

*(Para desarrollo sin Docker: Python 3.12+, Node 20+ y un PostgreSQL accesible.)*

## Instalación y ejecución

```bash
git clone <repositorio> energy-monitor
cd energy-monitor
cp .env.example .env          # ajusta la contraseña si lo deseas
docker compose up -d
```

La primera vez tarda unos minutos (construye imágenes y aplica migraciones).

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **frontend** | `APP_PORT` (por defecto **8080**) | Interfaz web (nginx + SPA) |
| backend | interno (8000) | API REST FastAPI |
| postgres | interno (5432) | Base de datos con volumen persistente |

Abre en tu navegador: **http://localhost:8080** (o `http://<ip-del-servidor>:8080` desde
otro equipo de la red local).

Detener: `docker compose down` (los datos se conservan). Eliminar datos: `docker compose down -v`.

## Estructura básica

```
energy-monitor/
├── backend/            # API FastAPI + SQLAlchemy + Alembic + tests pytest
│   ├── app/
│   │   ├── api/        # Rutas REST
│   │   ├── models/     # Modelos ORM (devices, energy_consumption, energy_rates, import_history)
│   │   ├── schemas/    # Contratos Pydantic
│   │   ├── services/   # Lógica de negocio (CSV, UPSERT, tarifas, costos, PDF, backup)
│   │   ├── repositories/ # Acceso a datos
│   │   ├── database/   # Motor, sesión, Base
│   │   └── main.py
│   ├── migrations/     # Migraciones Alembic
│   ├── tests/          # Suite pytest (CSV, UPSERT, tarifas, costos, PDF, API)
│   └── scripts/        # seed_demo.py (datos de demostración)
├── frontend/           # React 19 + TypeScript + Vite + Recharts
│   ├── src/pages/      # Dashboard, Dispositivos, Importar, Tarifas, Informes, Configuración
│   ├── src/components/
│   ├── assets/         # logo.png, favicon.png, default-device.png (reemplazables)
│   └── nginx.conf      # SPA + proxy /api
├── docs/               # Documentación completa
├── samples/            # CSVs de ejemplo
├── docker-compose.yml
├── .env.example
└── README.md
```

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | Instalación paso a paso (Docker y sin Docker) |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Guía de uso: dispositivos, CSV, tarifas, informes |
| [docs/CSV_FORMAT.md](docs/CSV_FORMAT.md) | Formato exacto del CSV y tratamiento de filas `total` |
| [docs/ASSETS.md](docs/ASSETS.md) | Cómo reemplazar logo/favicon/imagen por defecto |
| [docs/DATABASE.md](docs/DATABASE.md) | Modelo de datos, índices, restricciones y migraciones |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Tests, migraciones y desarrollo sin Docker |
| [docs/BACKUP.md](docs/BACKUP.md) | Backup y restauración (botón y pg_dump) |
| [docs/API.md](docs/API.md) | Referencia de todos los endpoints |
| [docs/FUTURAS_MEJORAS.md](docs/FUTURAS_MEJORAS.md) | Ideas futuras no incluidas en el MVP |

## Inicio rápido con datos de demostración

```bash
docker compose exec backend python scripts/seed_demo.py
```

Crea 4 dispositivos `[DEMO]` con ~8 meses de consumo y 3 tarifas. No toca datos reales.
Elimínalos con `python scripts/seed_demo.py --force`.
