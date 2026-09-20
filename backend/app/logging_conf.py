"""Configuración de logging (sección 47).

- Salida estándar (Docker la recoge).
- Registra: inicio/fin de importaciones, errores, errores de BD,
  generación de PDF y sus errores.
- NUNCA registra contraseñas ni secretos.
"""
from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(level)
    # Evitar duplicar handlers si se llama más de una vez
    root.handlers.clear()
    root.addHandler(handler)

    # Reducir ruido de librerías
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.WARNING)
