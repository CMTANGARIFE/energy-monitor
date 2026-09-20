# Base de datos

Energy Monitor usa **PostgreSQL** con acceso mediante **SQLAlchemy 2.0** (ORM) y
**Alembic** para migraciones.

## Modelo (MVP)

```
devices                 dispositivos monitoreados
├── id            PK
├── name          UNIQUE NOT NULL        (nombre único)
├── description   TEXT NULL
├── image         TEXT NULL              (nombre de archivo en frontend/assets/)
├── active        BOOLEAN DEFAULT true   (desactivación lógica, nunca borrado físico)
├── created_at / updated_at (UTC)

energy_consumption      consumo diario
├── id            PK
├── device_id     FK → devices.id ON DELETE RESTRICT
├── date          DATE NOT NULL          (DATE puro: consumo diario, SIN hora)
├── kwh           NUMERIC(12,4) NOT NULL CHECK (kwh >= 0)
├── created_at / updated_at (UTC)
└── UNIQUE(device_id, date)              ← clave lógica del UPSERT

energy_rates            tarifas COP/kWh por periodo
├── id            PK
├── start_date    DATE NOT NULL
├── end_date      DATE NULL              (NULL = vigente indefinidamente)
├── price_per_kwh NUMERIC(14,4) NOT NULL
├── created_at / updated_at (UTC)
└── [PostgreSQL] EXCLUDE USING gist (daterange) → impide solapamientos a nivel BD

import_history          auditoría de importaciones
├── id            PK
├── device_id     FK → devices.id ON DELETE SET NULL
├── filename      TEXT
├── imported_at   TIMESTAMPTZ (UTC)
├── records_found / records_inserted / records_updated / records_ignored INTEGER
├── status        'success' | 'error'
└── error_summary TEXT NULL
```

## Decisiones de diseño

- **`UNIQUE(device_id, date)`**: garantiza a nivel de base de datos que no existan
  duplicados por dispositivo y fecha; es el objetivo de conflicto del UPSERT
  (`INSERT ... ON CONFLICT (device_id, date) DO UPDATE`).
- **`CHECK kwh >= 0`**: los consumos negativos son imposibles.
- **Cero ≠ sin dato**: `kwh = 0` es un registro válido (día con consumo cero); la
  ausencia de fila significa *sin registro*. Las consultas y gráficas respetan esta
  diferencia y nunca rellenan con ceros.
- **`ON DELETE RESTRICT`** en consumo: un dispositivo con histórico nunca se borra
  físicamente (se desactiva con `active=false`).
- **Índices**: `ix_energy_consumption_device_id`, `ix_energy_consumption_date`
  (más el índice único compuesto) para consultas por dispositivo, por fecha y agregaciones.
- **Zona horaria**: `created_at`/`updated_at`/`imported_at` se guardan en UTC
  (`TIMESTAMPTZ`, `server_default=now()`); la interfaz convierte a hora local para mostrar.
- **Numérico decimal** (`NUMERIC`) en lugar de flotantes para kWh y precios: sin errores
  de redondeo acumulados.

## Restricción anti-solapamiento de tarifas

La migración `0002_pg_rates_exclude` intenta crear (en PostgreSQL):

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE energy_rates ADD CONSTRAINT ex_energy_rates_no_overlap
EXCLUDE USING gist (
  daterange(start_date,
            CASE WHEN end_date IS NULL THEN NULL::date
                 ELSE end_date + INTERVAL '1 day' END,
            '[]') WITH &&
);
```

Si la instalación de PostgreSQL no tiene disponible la extensión `btree_gist`
(poco habitual: la imagen oficial `postgres:16-alpine` la incluye), la migración lo
registra en el log y **continúa sin la restricción**: la regla se aplica igualmente a
nivel de aplicación (`app/services/rates.py`), que es la validación principal.

## Migraciones

```bash
# Aplicar (en Docker el backend lo hace automáticamente al arrancar)
docker compose exec backend alembic upgrade head

# Crear una nueva migración tras cambiar modelos
docker compose exec backend alembic revision --autogenerate -m "descripción"

# Historial y rollback
docker compose exec backend alembic history
docker compose exec backend alembic downgrade -1
```

El arranque en frío también incluye un *fallback* de seguridad: si la base está
totalmente vacía y por algún motivo no se ejecutó Alembic, `app/main.py` crea el esquema
con `Base.metadata.create_all` (y lo advierte en el log). En operación normal siempre
mandan las migraciones.

## Backup

Ver [BACKUP.md](BACKUP.md). El volumen `postgres_data` conserva los datos ante
`docker compose down` y recreación de contenedores.
