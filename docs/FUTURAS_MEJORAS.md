# Futuras mejoras

Ideas identificadas durante el desarrollo del MVP que **no fueron implementadas**
para mantener el sistema sencillo. Quedan documentadas como hoja de ruta y ninguna
es necesaria para el alcance actual.

## Alta utilidad percibida

- **Exportar CSV / Excel** de los consumos filtrados (el backend ya está estructurado
  con servicios para añadir un `export_service` sin tocar la API existente).
- **Backup automático programado** dentro del contenedor (cron + retención N días),
  complementando el botón actual y el pg_dump documentado.
- **Comparación entre periodos** en el Dashboard (p. ej. este mes vs. mes anterior,
  con variación porcentual por dispositivo).
- **Importación automática de carpeta vigilada**: apuntar el backend a una carpeta
  (volumen compartido) e importar CSVs nuevos que aparezcan, reutilizando el
  importador actual.

## Medianas

- **Consumo horario**: requiere cambiar la granularidad del modelo (hoy la clave es
  device+date). Diseñar una tabla `energy_consumption_hourly` en lugar de migrar la
  actual, para no romper el histórico diario.
- **Alertas** por umbrales (consumo diario/costos superiores a X) — puede hacerse por
  banner en Dashboard y por correo.
- **Reportes programados**: generar el PDF mensual automáticamente y dejarlo en una
  carpeta o enviarlo por correo.
- **Predicción de consumo/costo de cierre de mes** (regresión simple sobre los últimos
  30 días; sin IA pesada).
- **Múltiples monedas** y **unidades de energía** (Wh/MWh): el modelo guarda COP y kWh
  como constantes de configuración; haría falta una tabla de monedas y factor de unidad
  por dispositivo.
- **Tarifas más complejas** (por rangos horarios, subsidios, aportes): el modelo actual
  solo soporta precio fijo por periodo, según especificación del MVP.

## Menores / infraestructura

- **Autenticación** y **múltiples usuarios**: el MVP se define para red local confiable
  sin cuentas. Si se abre fuera de casa, añadir al menos un proxy con contraseña
  (o Tailscale, que no requiere cambios en la app).
- **Acceso remoto mediante Tailscale/WireGuard**: documentar guía paso a paso.
- **Instalación remota** en VPS: cambia el modelo de confianza (CORS, autenticación).
- **Integración IoT/medidores**: fuera de alcance del MVP; añadiría un importador
  alternativo que alimenta el mismo modelo de datos.
- **PWA**: manifest + service worker para "instalar" la app en móvil.
- **Tema oscuro**: el CSS ya usa variables; es viable con bajo esfuerzo.

## Descartadas deliberadamente para este proyecto

- Nube / servicios externos (el diseño es 100% local).
- Kubernetes / microservicios (excesivo para una instalación doméstica).
- Facturación real e impuestos (cálculo estimado, no oficial).
- IA / funciones no solicitadas.
