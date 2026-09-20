"""Excepciones de dominio con mensajes claros para usuarios no técnicos.

La API las traduce a respuestas HTTP con `detail` legible (sección 46):
los detalles técnicos completos quedan en los logs del backend.
"""
from __future__ import annotations


class EnergyMonitorError(Exception):
    """Base de errores de dominio."""


class NotFoundError(EnergyMonitorError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConflictError(EnergyMonitorError):
    """Conflicto de datos (nombre duplicado, solapamiento de tarifas, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(EnergyMonitorError):
    """Datos de entrada inválidos (CSV mal formado, tarifas incoherentes...)."""

    def __init__(self, message: str, errors: list[dict] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or []


class RateOverlapError(ConflictError):
    """Periodos de tarifas solapados."""
