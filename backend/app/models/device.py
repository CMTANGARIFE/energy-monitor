"""Modelo Device: dispositivos monitoreados.

- El nombre es único.
- No se eliminan físicamente dispositivos con datos históricos:
  se usa desactivación lógica (active=False).
"""
from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class Device(TimestampMixin, Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nombre de archivo de imagen dentro de assets/ (p. ej. default-device.png)
    image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    consumptions = relationship(
        "EnergyConsumption",
        back_populates="device",
        cascade=["save-update", "merge"],  # NO delete: los datos históricos se conservan
        passive_deletes=True,
    )
    imports = relationship("ImportHistory", back_populates="device", passive_deletes=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Device id={self.id} name={self.name!r} active={self.active}>"
