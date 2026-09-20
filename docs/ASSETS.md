# Assets reemplazables

Los recursos visuales de Energy Monitor están en carpetas `assets/` y pueden
**reemplazarse sin modificar ningún código**.

## Ubicación

```
energy-monitor/
├── frontend/
│   └── assets/            ← se sirve en http://<host>:8080/assets/
│       ├── logo.png
│       ├── favicon.png
│       └── default-device.png
└── backend/
    └── assets/            ← lo usa el generador de PDF
        └── logo.png
```

En Docker ambas carpetas están **montadas como volúmenes**: al reemplazar un archivo no
hace falta reconstruir la imagen, solo **refrescar el navegador** (Ctrl+F5) o, en el peor
caso, reiniciar el backend:

```bash
docker compose restart backend
```

## Archivos y especificaciones

| Archivo | Formato | Dimensiones recomendadas | Transparencia | Propósito | Ubicación |
|---------|---------|--------------------------|---------------|-----------|-----------|
| `logo.png` | PNG | 512×512 | Sí (fondo transparente) | Logo principal: menú lateral, topbar móvil y cabecera del PDF | `frontend/assets/` **y** `backend/assets/` |
| `favicon.png` | PNG | 64×64 | Sí | Ícono de la pestaña del navegador | `frontend/assets/` |
| `default-device.png` | PNG | 256×256 | Sí | Imagen por defecto de los dispositivos que no tienen una propia | `frontend/assets/` |

## Cómo reemplazar (ejemplo: cambiar el logo)

1. Prepara la nueva imagen en PNG con las dimensiones recomendadas y fondo transparente.
2. **Renómbrala exactamente** igual que el archivo a sustituir (por ejemplo `logo.png`).
3. Reemplaza el archivo:
   - `frontend/assets/logo.png` (interfaz)
   - `backend/assets/logo.png` (informes PDF)
4. Refresca el navegador con caché vacía (Ctrl+F5). Para el PDF no hace falta nada más:
   se lee al generar cada informe.

No hay que tocar código, recompilar ni reiniciar (salvo que el navegador cachee el favicon:
puede requerir recargar de nuevo o abrir en ventana incógnito).

## Imágenes de dispositivos

Cada dispositivo puede tener una imagen personalizada:

1. Copia tu imagen (PNG, recomendado 256×256 con transparencia) en `frontend/assets/`
   con un nombre descriptivo, por ejemplo `nevera.png`.
2. En **Dispositivos → Editar**, escribe `nevera.png` en el campo *Imagen / icono*.
3. Guarda. Si el campo se deja vacío se usa `default-device.png`.

> La imagen se referencia por **nombre de archivo dentro de `frontend/assets/`**, nunca por
> ruta absoluta ni URL externa. El backend valida el nombre y la ruta se resuelve siempre
> dentro de esa carpeta (sin path traversal).
