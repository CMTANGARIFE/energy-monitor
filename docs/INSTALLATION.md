# Instalación

## Opción A — Docker Compose (recomendada)

### Requisitos
- Docker Engine 24 o superior
- Docker Compose v2 (comando `docker compose`)

### Pasos

```bash
# 1. Clonar el repositorio
git clone <repositorio> energy-monitor
cd energy-monitor

# 2. Crear el archivo de entorno a partir del ejemplo
cp .env.example .env

# 3. (Recomendado) Editar .env y cambiar la contraseña:
#    POSTGRES_PASSWORD=una_clave_segura_local
nano .env

# 4. Construir y levantar los servicios
docker compose up -d

# 5. Verificar que todo arrancó
docker compose ps
docker compose logs backend --tail 30
```

El backend aplica automáticamente las migraciones Alembic al arrancar
(entrypoint.sh espera a PostgreSQL y ejecuta `alembic upgrade head`).

### Acceso

- Desde el servidor: **http://localhost:8080**
- Desde otro equipo de la red local: **http://<ip-del-servidor>:8080**

El puerto se cambia con la variable `APP_PORT` en `.env` (luego `docker compose up -d`).

### Verificación del estado

```bash
curl http://localhost:8080/health
# {"status":"ok","database":"ok", ...}
```

### Datos de demostración (opcional)

```bash
docker compose exec backend python scripts/seed_demo.py
```

### Actualizar la aplicación

```bash
git pull
docker compose build
docker compose up -d
```

## Opción B — Sin Docker (desarrollo)

### Requisitos
- Python 3.12+
- Node.js 20+ y npm
- Un servidor PostgreSQL 14+ accesible

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Apuntar a tu PostgreSQL
export DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/energy_monitor

# Migraciones
alembic upgrade head

# Arrancar la API (puerto 8000)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxía /api al backend 8000)
```

### Documentación interactiva de la API

Con el backend corriendo: http://localhost:8000/docs (Swagger UI generado por FastAPI).

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `backend` se reinicia en bucle | PostgreSQL aún no listo | Espera 30 s; el entrypoint reintenta 60 s |
| `frontend` responde 502 | Backend caído | `docker compose logs backend` |
| No accede desde otro equipo | Puerto/firewall | Abre `APP_PORT` en el firewall; usa la IP del servidor |
| Contraseña cambiada tras crear volumen | Volumen con clave anterior | Borra el volumen: `docker compose down -v` (¡pierdes datos!) |
