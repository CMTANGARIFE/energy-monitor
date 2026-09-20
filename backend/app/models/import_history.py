"""Modelo ImportHistory: auditoría de cada importación CSV.

No se guarda el CSV completo, solo el resumen (auditoría y diagnóstico).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ImportHistory(Base):
    __tablename__ = "import_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    records_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_ignored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 'success' | 'error'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    device = relationship("Device", back_populates="imports")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ImportHistory id={self.id} device={self.device_id} status={self.status}>"
