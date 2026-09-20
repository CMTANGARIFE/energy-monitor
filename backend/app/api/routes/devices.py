"""CRUD de dispositivos (secciones 16-17 de la especificación).

- El nombre debe ser único.
- No existe DELETE físico: se usa desactivación lógica (active=False)
  para conservar los datos históricos.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.devices import DeviceRepository
from app.schemas.device import (
    DeviceCreate,
    DeviceDetail,
    DeviceOut,
    DeviceStatusUpdate,
    DeviceUpdate,
)

router = APIRouter(prefix="/devices", tags=["dispositivos"])


@router.get("", response_model=list[DeviceOut])
def list_devices(
    active_only: bool = Query(default=False, description="Solo dispositivos activos"),
    db: Session = Depends(get_db),
):
    """Lista de dispositivos (opcionalmente solo activos)."""
    return DeviceRepository(db).list(active_only=active_only)


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    """Crea un dispositivo. El nombre debe ser único."""
    repo = DeviceRepository(db)
    if repo.get_by_name(payload.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un dispositivo con el nombre '{payload.name}'.",
        )
    return repo.create(
        name=payload.name.strip(),
        description=payload.description,
        image=payload.image,
    )


@router.get("/{device_id}", response_model=DeviceDetail)
def get_device(device_id: int, db: Session = Depends(get_db)):
    """Información detallada del dispositivo + resumen de histórico."""
    device = DeviceRepository(db).get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="El dispositivo indicado no existe.")
    summary = DeviceRepository(db).lifetime_summary(device_id)
    return DeviceDetail(
        **{
            "id": device.id,
            "name": device.name,
            "description": device.description,
            "image": device.image,
            "active": device.active,
            "created_at": device.created_at,
            "updated_at": device.updated_at,
            **summary,
        }
    )


@router.put("/{device_id}", response_model=DeviceOut)
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)):
    """Edita nombre, descripción e imagen del dispositivo."""
    repo = DeviceRepository(db)
    device = repo.get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="El dispositivo indicado no existe.")
    if payload.name is not None:
        existing = repo.get_by_name(payload.name)
        if existing and existing.id != device_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un dispositivo con el nombre '{payload.name}'.",
            )
    return repo.update(
        device,
        name=payload.name.strip() if payload.name else None,
        description=payload.description,
        image=payload.image,
    )


@router.patch("/{device_id}/status", response_model=DeviceOut)
def set_device_status(device_id: int, payload: DeviceStatusUpdate, db: Session = Depends(get_db)):
    """Activa o desactiva un dispositivo (desactivación lógica)."""
    repo = DeviceRepository(db)
    device = repo.get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="El dispositivo indicado no existe.")
    return repo.set_status(device, payload.active)
