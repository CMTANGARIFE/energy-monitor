"""Esquemas de tarifas."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RateBase(BaseModel):
    start_date: dt.date
    end_date: dt.date | None = None
    price_per_kwh: Decimal = Field(gt=0, max_digits=14, decimal_places=4)


class RateCreate(RateBase):
    pass


class RateUpdate(BaseModel):
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    price_per_kwh: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=4)


class RateOut(RateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: dt.datetime
    updated_at: dt.datetime
