"""Esquemas Pydantic (contratos de la API)."""
from app.schemas.common import ErrorDetail, Message, PeriodInfo
from app.schemas.consumption import (
    ConsumptionDailyPoint,
    ConsumptionDeviceRow,
    ConsumptionSummary,
    DeviceConsumptionStats,
)
from app.schemas.device import DeviceCreate, DeviceDetail, DeviceOut, DeviceStatusUpdate, DeviceUpdate
from app.schemas.import_ import ImportPreview, ImportPreviewRequest, ImportResult, ImportHistoryOut
from app.schemas.rate import RateCreate, RateOut, RateUpdate

__all__ = [
    "ErrorDetail", "Message", "PeriodInfo",
    "ConsumptionDailyPoint", "ConsumptionDeviceRow", "ConsumptionSummary", "DeviceConsumptionStats",
    "DeviceCreate", "DeviceDetail", "DeviceOut", "DeviceStatusUpdate", "DeviceUpdate",
    "ImportPreview", "ImportPreviewRequest", "ImportResult", "ImportHistoryOut",
    "RateCreate", "RateOut", "RateUpdate",
]
