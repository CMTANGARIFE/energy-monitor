# Formato del CSV de consumo

## Estructura

```csv
date,kwh,cost
2026/03/15,0,0
2026/03/16,0,0
2026/03/17,0,0
2026/03/24,2.34,0
2026/03/25,1.18,0
total,8.57,0.00
2026/04/01,1.20,0
```

Ejemplo completo: [`samples/consumo_pc_ejemplo.csv`](../samples/consumo_pc_ejemplo.csv).

## Columnas

| Columna | Obligatoria | Uso |
|---------|-------------|-----|
| `date` | **Sí** | Fecha del día en formato `YYYY/MM/DD` |
| `kwh`  | **Sí** | Consumo del día en kWh (número ≥ 0) |
| `cost` | No | **IGNORADA por diseño.** El costo lo calcula Energy Monitor con las tarifas configuradas |

Pueden haber columnas extra: se ignoran. Los encabezados se comparan sin distinguir
mayúsculas ni espacios (`Date`, `KWH` funcionan).

## Reglas importantes

### 1. Filas `total` se ignoran

Las filas cuya posición de fecha contiene la palabra `total` (por ejemplo `total,8.57,0.00`)
**no representan un día**. Se descartan por completo y **no** se almacenan como consumo.
Energy Monitor calcula sus propios totales sumando las filas diarias.

### 2. La columna `cost` no se almacena

Aunque el CSV traiga un costo, **nunca** se guarda: todos los costos se calculan internamente
con las tarifas configuradas en la aplicación (sección Tarifas). Así los costos son
coherentes y actualizables.

### 3. Formato de fecha estricto: `YYYY/MM/DD`

Ejemplo válido: `2026/03/24`. Formatos como `24/03/2026`, `2026-03-24` o `24-03-2026`
son **rechazados** con un error que indica la fila exacta. Internamente la fecha se guarda
como `DATE` de PostgreSQL (sin hora).

### 4. kWh válido

- Número con punto decimal: `2.34`.
- **`0` es un dato válido** y se almacena: significa *día con consumo cero* (distinto de
  *día sin registro*).
- Negativos, no numéricos, `NaN` o infinitos son rechazados con detalle de la fila.

### 5. Fechas duplicadas dentro del mismo CSV

Si el mismo archivo contiene dos filas para la misma fecha:

```csv
2026/03/24,2.34,0
2026/03/24,4.56,0
```

la importación se **rechaza completa** (no se elige una arbitrariamente). Corrige el archivo
y vuelve a intentarlo.

### 6. Actualización (UPSERT) con datos ya existentes

La clave lógica es **dispositivo + fecha**. Al importar:

- fecha **nueva** → se **inserta**;
- fecha **ya existente** para ese dispositivo → se **actualiza** el kWh.

Ejemplo:

| Fecha | Base existente | CSV nuevo | Resultado |
|-------|---------------|-----------|-----------|
| 24/03 | 2.34 | 5.00 | **5.00** (actualizado) |
| 25/03 | 1.18 | — | 1.18 (intacto) |
| 26/03 | 0.00 | — | 0.00 (intacto) |
| 27/03 | — | 3.00 | **3.00** (nuevo) |

Reimportar un CSV corregido es la forma correcta de corregir datos.

### 7. Errores por fila

Si alguna fila es inválida, la importación NO guarda nada (operación transaccional) y la
aplicación muestra, por cada problema: **número de fila**, **valor problemático** y **motivo**.

Ejemplo:

```
No se pudo importar el archivo: contiene errores de validación.
- Fila 37 — valor "2026/99/45": Fecha inválida. Se requiere el formato YYYY/MM/DD.
```

### 8. Tamaño y codificación

- Tamaño máximo configurable (`MAX_CSV_SIZE_MB`, por defecto 10 MB).
- Codificaciones aceptadas: UTF-8 (con o sin BOM) y Latin-1.
- Solo archivos `.csv` o `.txt` de texto.
