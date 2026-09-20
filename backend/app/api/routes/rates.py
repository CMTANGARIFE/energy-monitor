"""CRUD de tarifas de energía (secciones 18-19).

Reglas aplicadas en el servicio:
- Sin periodos solapados (409 al intentar).
- Máximo una tarifa abierta (end_date NULL).
- end_date >= start_date y precio > 0.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.rate import RateCreate, RateOut, RateUpdate
from app.services.errors import ConflictError, NotFoundError, ValidationError
from app.services.rates import RateService

router = APIRouter(prefix="/rates", tags=["tarifas"])


@router.get("", response_model=list[RateOut])
def list_rates(
    date_from=None,
    date_to=None,
    db: Session = Depends(get_db),
):
    """Lista de tarifas ordenadas por fecha inicial."""
    return RateService(db).repo.list(date_from=date_from, date_to=date_to)


@router.post("", response_model=RateOut, status_code=status.HTTP_201_CREATED)
def create_rate(payload: RateCreate, db: Session = Depends(get_db)):
    """Crea una tarifa. Rechaza solapamientos y más de una tarifa abierta."""
    try:
        return RateService(db).create(payload.start_date, payload.end_date, payload.price_per_kwh)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc


@router.put("/{rate_id}", response_model=RateOut)
def update_rate(rate_id: int, payload: RateUpdate, db: Session = Depends(get_db)):
    try:
        return RateService(db).update(rate_id, payload.model_dump(exclude_unset=True))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rate(rate_id: int, db: Session = Depends(get_db)):
    try:
        RateService(db).delete(rate_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    return None
