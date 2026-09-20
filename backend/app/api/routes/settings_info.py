"""Información para la página de Configuración de la app."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.models import Device, EnergyConsumption, EnergyRate, ImportHistory
from app.services.pdf_report import logo_path

router = APIRouter(tags=["configuración"])


@router.get("/settings/info")
def settings_info(db: Session = Depends(get_db)):
    """Información general de la instalación (versión, moneda, assets)."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "currency": settings.currency,
        "max_csv_size_mb": settings.max_csv_size_mb,
        "database_engine": settings.database_url.split("://")[0].split("+")[0],
        "pdf_logo_available": logo_path() is not None,
        "default_device_image": settings.default_device_image,
    }


@router.get("/settings/stats")
def settings_stats(db: Session = Depends(get_db)):
    """Conteos globales para la página de configuración."""
    from sqlalchemy import func, select

    return {
        "devices": db.scalar(select(func.count(Device.id))) or 0,
        "consumption_records": db.scalar(select(func.count(EnergyConsumption.id))) or 0,
        "rates": db.scalar(select(func.count(EnergyRate.id))) or 0,
        "imports": db.scalar(select(func.count(ImportHistory.id))) or 0,
    }
