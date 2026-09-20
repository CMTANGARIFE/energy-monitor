# Backup y restauración

La información histórica debe sobrevivir a reinicios, recreación de contenedores y fallos.
Energy Monitor ofrece dos mecanismos: el **botón de la aplicación** y el **procedimiento
manual con pg_dump**. Ambos producen un volcado SQL de la base de datos completa.

---

## 1. Backup desde la aplicación

**Configuración → ⬇ Descargar backup**

- En producción (PostgreSQL) ejecuta `pg_dump` con las credenciales del sistema y descarga
  un archivo `energy_monitor_backup_YYYYMMDD_HHMMSS.sql`.
- Si `pg_dump` no está disponible (p. ej. instalación de desarrollo sin PostgreSQL), la
  descarga es un volcado JSON de compatibilidad.

> El endpoint es local y sin autenticación por diseño del MVP; en instalaciones expuestas
> a más usuarios conviene restringir el acceso al puerto de la aplicación a la red confiable.

## 2. Backup manual (recomendado para automatizar)

### Crear

```bash
# Volcado SQL completo (estructura + datos), comprimido
docker compose exec -T postgres pg_dump -U energy -d energy_monitor \
  --no-owner --no-privileges | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

- `-U energy`: usuario de `POSTGRES_USER` en `.env`.
- `-d energy_monitor`: base de datos de `POSTGRES_DB`.
- El `-T` evita que gzip corrompa el binario al pasar por el pipe.

> También puede dejarse sin comprimir: `docker compose exec -T postgres pg_dump -U energy -d energy_monitor > backup.sql`

### Dónde queda

El archivo queda en la carpeta **desde donde ejecutaste el comando** (el host), no dentro
del contenedor. Sugerencia: mantenerlos en `~/backups/energy-monitor/` o similar,
fuera del repositorio.

### Automatizar (ejemplo con cron, diario a las 3:00)

```bash
crontab -e
# Añadir:
0 3 * * * cd /ruta/a/energy-monitor && docker compose exec -T postgres pg_dump -U energy -d energy_monitor --no-owner --no-privileges | gzip > ~/backups/energy-monitor/diario_$(date +\%Y\%m\%d).sql.gz
```

## 3. Restaurar

### Base de datos vacía (o recién creada)

```bash
# 1. Asegúrate de que los contenedores están levantados
docker compose up -d

# 2. Restaura el volcado (descomprime y ejecuta)
gunzip -c backup_20260101_030000.sql.gz | docker compose exec -T postgres psql -U energy -d energy_monitor

# 3. Reinicia el backend para que recargue el esquema
docker compose restart backend
```

### Reemplazar TODO lo actual por el backup

```bash
# ¡Cuidado! Borra los datos actuales
docker compose stop backend frontend
docker compose exec postgres psql -U energy -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='energy_monitor' AND pid <> pg_backend_pid();"
docker compose exec postgres psql -U energy -d postgres -c "DROP DATABASE energy_monitor;"
docker compose exec postgres psql -U energy -d postgres -c "CREATE DATABASE energy_monitor OWNER energy;"
gunzip -c backup_20260101_030000.sql.gz | docker compose exec -T postgres psql -U energy -d energy_monitor
docker compose start backend frontend
```

Tras restaurar, `alembic upgrade head` no es necesario si el backup ya incluye la tabla
`alembic_version` (los backups completos la incluyen).

## 4. ¿Qué ocurre si se pierde el contenedor PostgreSQL?

- **Solo el contenedor** (los datos estaban en el volumen `postgres_data`): recrear el
  contenedor con `docker compose up -d` **no pierde datos**; el volumen persiste.
- **El volumen se perdió** (borrado accidental, disco dañado): recrea con
  `docker compose up -d` y luego **restaura el último backup** como en la sección 3.
- Por eso es importante el backup periódico automatizado: el volumen protege de reinicios
  y recreaciones, el backup protege de pérdidas del volumen.

## 5. Verificación periódica recomendada

1. Cada mes, descarga un backup (botón o pg_dump).
2. En un entorno de prueba, restaura y verifica: dispositivos, consumos de un periodo
   conocido y tarifas.
3. Un backup que nunca se ha probado restaurar no es un backup: es una esperanza.
