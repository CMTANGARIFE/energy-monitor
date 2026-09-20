"""Mixin de timestamps consistentes.

Estrategia de zona horaria (sección 43 de la especificación):
- Internamente SIEMPRE en UTC (DateTime(timezone=True) + server_default=now()
  sobre una BD configurada en UTC).
- La interfaz puede convertir a zona local al mostrar.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
