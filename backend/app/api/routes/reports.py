"""Generación de informes PDF (secciones 26-28)."""
from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.errors import EnergyMonitorError
from app.services.pdf_report import PDFReportService

logger = logging.getLogger("energy_monitor.api.pdf")
router = APIRouter(tags=["informes"])


class ReportRequest(BaseModel):
    date_from: dt.date
    date_to: dt.date
    device_ids: list[int] | None = Field(
        default=None, description="IDs de dispositivos. None = todos los dispositivos."
    )


@router.post("/reports/pdf")
def generate_pdf_report(payload: ReportRequest, db: Session = Depends(get_db)):
    """Genera el informe PDF del periodo y dispositivos seleccionados.

    Incluye: resumen general, tabla por dispositivo, gráficas (diario total,
    por dispositivo, diario por dispositivo), tarifas usadas y advertencias.
    """
    if payload.date_to < payload.date_from:
        raise HTTPException(
            status_code=422,
            detail="La fecha final del informe no puede ser anterior a la fecha inicial.",
        )
    logger.info(
        "Generación de PDF solicitada: %s a %s dispositivos=%s",
        payload.date_from, payload.date_to, payload.device_ids or "todos",
    )
    try:
        pdf_bytes = PDFReportService(db).generate(
            date_from=payload.date_from,
            date_to=payload.date_to,
            device_ids=payload.device_ids,
        )
    except EnergyMonitorError as exc:
        logger.error("Error de datos generando PDF: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error crítico generando PDF")
        raise HTTPException(
            status_code=500,
            detail="No se pudo generar el informe PDF. Revise los logs del backend.",
        ) from exc

    filename = f"informe_energia_{payload.date_from.strftime('%Y%m%d')}_{payload.date_to.strftime('%Y%m%d')}.pdf"
    logger.info("PDF generado correctamente: %s (%s bytes)", filename, len(pdf_bytes))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
