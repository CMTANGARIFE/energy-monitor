# Guía de usuario

Esta guía explica el uso diario de Energy Monitor paso a paso. No se requieren
conocimientos técnicos.

## 1. Crear un dispositivo

1. En el menú lateral entra a **Dispositivos**.
2. Pulsa **+ Agregar dispositivo**.
3. Escribe el **nombre** (obligatorio, único). Ejemplos: `PC Principal`, `Nevera`, `Servidor`.
4. Añade una **descripción** opcional y una **imagen** opcional (ver [ASSETS.md](ASSETS.md)).
5. Pulsa **Guardar**.

> Los dispositivos **no se eliminan físicamente**: al desactivarlos desaparecen de las
> selecciones pero conservan todo su histórico. Puedes reactivarlos cuando quieras.

## 2. Importar un CSV de consumo

1. Entra a **Importar consumo**.
2. **Arrastra** el archivo CSV a la zona indicada o haz clic para seleccionarlo.
   El formato esperado es `date,kwh,cost` con fechas `YYYY/MM/DD` (ver [CSV_FORMAT.md](CSV_FORMAT.md)).
3. Verás el resumen del archivo (nombre, tamaño, registros, periodo detectado) y
   elegirás el **dispositivo** asociado.
4. Pulsa **Continuar**: aparece la **vista previa** con:
   - registros encontrados,
   - registros nuevos,
   - registros existentes que serán **actualizados**,
   - filas `total` ignoradas.
5. Pulsa **Continuar** y luego **IMPORTAR DATOS**.
6. Verás el resultado: *Registros nuevos: N · Actualizados: M · Filas ignoradas: K ·
   Consumo procesado: XX.XX kWh*.

> **UPSERT**: si ya existía un registro del mismo dispositivo para una fecha, su kWh se
> **actualiza** con el valor del CSV; si era nuevo, se **inserta**. Nunca se crean duplicados.
> Si el CSV tiene errores (fecha inválida, kWh negativo…), verás la fila exacta y el motivo,
> y **nada se guardará**.

## 3. Configurar tarifas

1. Entra a **Tarifas** y pulsa **+ Nueva tarifa**.
2. Indica **Desde** (obligatorio), **Hasta** (opcional: déjala "Vigente indefinida" si aún
   no sabes cuándo cambiará) y el **precio por kWh en COP**.
3. Guarda.

Reglas aplicadas automáticamente:
- Los periodos **no pueden solaparse** (te avisará si intentas crear uno que cruce otro).
- Solo puede existir **una tarifa abierta** (sin fecha final).
- Precio mayor que cero.

**Cómo se calcula el costo:** cada día de consumo multiplica su kWh por la tarifa vigente
*en esa fecha concreta*. Si un informe atraviesa dos tarifas, cada tramo usa la suya.

## 4. Consultar el consumo (Dashboard)

1. Ve al **Dashboard**.
2. Usa los accesos rápidos: *Hoy, Últimos 7 días, Últimos 30 días, Este mes, Mes anterior,
   Este año, Personalizado*; o escribe las fechas manualmente.
3. En **Dispositivo(s)** elige todos o uno/several concretos.
4. Analiza las tarjetas (consumo total, costo estimado, promedio diario, nº dispositivos)
   y las 5 gráficas:
   - **Consumo diario total** (línea),
   - **Consumo diario por dispositivo** (una línea por equipo; los huecos = días sin registro),
   - **Consumo acumulado**,
   - **Consumo por dispositivo** (barras),
   - **Costo diario estimado** (usa las tarifas; días sin tarifa aparecen como huecos y hay aviso).

## 5. Página de dispositivo

Pulsa el nombre de un dispositivo para ver: su información, estadísticas (total, promedio,
máximo y mínimo diario con su fecha, día de mayor/menor consumo, costo estimado, primer y
último día registrado), gráficas, su historial de importaciones y las tarifas aplicables.

## 6. Generar un informe PDF

1. Ve a **Informes**.
2. Selecciona el **periodo** (fechas o acceso rápido).
3. Selecciona **Todos los dispositivos** o uno/varios concretos.
4. Pulsa **GENERAR INFORME PDF**; se descargará el archivo.

El PDF incluye: encabezado con logo, resumen general, tabla por dispositivo con TOTAL,
gráficas de consumo (diario total, por dispositivo y diario por dispositivo), tarifas
utilizadas y advertencias (días sin tarifa, días sin datos). Pie con numeración
"Página X de Y" y fecha de generación.

## 7. Backup y restauración

- **Desde la app**: Configuración → **⬇ Descargar backup** (volcado SQL de la base de datos).
- **Manual**: ver [BACKUP.md](BACKUP.md) (`docker compose exec postgres pg_dump ...`).

Los datos también sobreviven a reinicios y recreación de contenedores gracias al volumen
persistente. Aun así, haz backups periódicos.

## 8. Consejos

- Importa periódicamente: la importación es acumulativa (no borra nada).
- Reimportar el mismo CSV actualizado **corrige** los valores ya guardados.
- Si ves el aviso "Tarifa no configurada", crea la tarifa del periodo y el costo se
  calculará a partir de entonces (los días previos seguirán sin costo; no se inventan).
