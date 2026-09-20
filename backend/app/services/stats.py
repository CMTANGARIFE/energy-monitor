"""Servicio de estadísticas y agregaciones.

Puntos clave (especificación):
- "0 kWh registrado" es distinto de "día sin registro": las series solo
  contienen días con registro real (secciones 54-55).
- Costos calculados día a día con la tarifa aplicable (sección 20).
- Días sin tarifa y días sin datos se reportan sin inventar valores.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.repositories.consumption import ConsumptionRepository, daterange
from app.repositories.devices import DeviceRepository
from app.schemas.consumption import (
    ConsumptionDailyPoint,
    DevicePeriodCost,
    DeviceConsumptionStats,
)
from app.services.costs import CostCalculator
from app.services.errors import NotFoundError


class StatsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.consumptions = ConsumptionRepository(db)
        self.devices = DeviceRepository(db)

    # ------------------------------------------------------------------
    # Resumen de periodo para uno o varios dispositivos (Dashboard/PDF)
    # ------------------------------------------------------------------
    def period_summary(
        self, device_ids: list[int], date_from: dt.date, date_to: dt.date
    ) -> dict:
        devices = {d.id: d for d in self.devices.list() if d.id in set(device_ids)}
        if not devices:
            raise NotFoundError("No hay dispositivos que analizar en el periodo.")

        rows = self.consumptions.daily_totals_by_device(device_ids, date_from, date_to)

        # --- Mapa diario: fecha -> {device_id: kwh} (solo días CON registro)
        daily_by_device: dict[dt.date, dict[int, float]] = {}
        for day, dev_id, kwh in rows:
            daily_by_device.setdefault(day, {})[dev_id] = float(kwh)

        # --- Series para gráficas (solo días con datos)
        series: list[ConsumptionDailyPoint] = []
        daily_total: dict[dt.date, float] = {}
        for day in sorted(daily_by_device):
            values = daily_by_device[day]
            total = sum(values.values())
            daily_total[day] = total
            series.append(
                ConsumptionDailyPoint(
                    date=day,
                    total=round(total, 4),
                    values={str(k): round(v, 4) for k, v in values.items()},
                )
            )

        period_days = (date_to - date_from).days + 1
        days_with_data = len(daily_by_device)

        # --- Totales por dispositivo
        by_device: list[DevicePeriodCost] = []
        for dev_id in device_ids:
            device = devices.get(dev_id)
            if device is None:
                continue
            dev_daily = {
                day: values.get(dev_id)
                for day, values in daily_by_device.items()
                if dev_id in values
            }
            dev_kwh = sum(dev_daily.values())
            dev_cost, dev_missing = CostCalculator(self.db, date_from, date_to).total_cost(dev_daily)
            by_device.append(
                DevicePeriodCost(
                    device_id=dev_id,
                    device_name=device.name,
                    kwh=round(dev_kwh, 4),
                    cost=float(dev_cost) if dev_cost is not None else None,
                    cost_incomplete=bool(dev_missing),
                    days_without_rate=len(dev_missing),
                )
            )

        # --- Costos del total diario (todas las tarifas del periodo)
        calc = CostCalculator(self.db, date_from, date_to)
        total_cost, missing_days = calc.total_cost(daily_total)

        # --- Serie de costo diario (para Gráfica E); None = día sin tarifa
        cost_series = [
            {
                "date": day.isoformat(),
                "cost": float(cost) if (cost := calc.cost_for(day, kwh)) is not None else None,
            }
            for day, kwh in sorted(daily_total.items())
        ]

        # --- Estadísticas diarias
        totals = list(daily_total.values())
        max_day = max(daily_total, key=daily_total.get) if daily_total else None
        min_day = min(daily_total, key=daily_total.get) if daily_total else None

        return {
            "date_from": date_from,
            "date_to": date_to,
            "days": period_days,
            "devices_count": len(by_device),
            "total_kwh": round(sum(totals), 4) if totals else 0.0,
            "avg_daily_kwh": round(sum(totals) / len(totals), 4) if totals else None,
            "max_daily_kwh": round(daily_total[max_day], 4) if max_day else None,
            "max_daily_date": max_day,
            "min_daily_kwh": round(daily_total[min_day], 4) if min_day else None,
            "min_daily_date": min_day,
            "first_data_date": min(daily_by_device) if daily_by_device else None,
            "last_data_date": max(daily_by_device) if daily_by_device else None,
            "days_with_data": days_with_data,
            "days_without_data": period_days - days_with_data,
            "total_cost": float(total_cost) if total_cost is not None else None,
            "cost_incomplete": bool(missing_days),
            "days_without_rate": len(missing_days),
            "missing_rate_ranges": calc.missing_rate_ranges(missing_days),
            "by_device": by_device,
            "series": series,  # serie diaria combinada para gráficas
            "cost_series": cost_series,  # costo diario para Gráfica E
            "daily_by_device": daily_by_device,  # para PDF/series por dispositivo
        }

    # ------------------------------------------------------------------
    # Series por dispositivo (Gráfica B: consumo diario por dispositivo)
    # ------------------------------------------------------------------
    def per_device_series(
        self, device_ids: list[int], date_from: dt.date, date_to: dt.date
    ) -> dict[int, list[dict]]:
        """{device_id: [{date, kwh}, ...]} con solo días con registro."""
        rows = self.consumptions.daily_totals_by_device(device_ids, date_from, date_to)
        result: dict[int, list[dict]] = {dev_id: [] for dev_id in device_ids}
        for day, dev_id, kwh in rows:
            result.setdefault(dev_id, []).append({"date": day.isoformat(), "kwh": float(kwh)})
        for dev_id in result:
            result[dev_id].sort(key=lambda item: item["date"])
        return result

    # ------------------------------------------------------------------
    # Serie acumulada (Gráfica C)
    # ------------------------------------------------------------------
    @staticmethod
    def cumulative_series(series: list[ConsumptionDailyPoint]) -> list[dict]:
        cumulative: list[dict] = []
        running = 0.0
        for point in series:
            running += point.total
            cumulative.append({"date": point.date.isoformat(), "kwh": round(running, 4)})
        return cumulative

    # ------------------------------------------------------------------
    # Estadísticas de un dispositivo concreto (sección 24)
    # ------------------------------------------------------------------
    def device_stats(self, device_id: int, date_from: dt.date, date_to: dt.date) -> dict:
        device = self.devices.get(device_id)
        if device is None:
            raise NotFoundError("El dispositivo indicado no existe.")

        summary = self.period_summary([device_id], date_from, date_to)
        period_cost = summary["by_device"][0] if summary["by_device"] else None

        device_days = [day for day, values in summary["daily_by_device"].items() if device_id in values]
        first_day = min(device_days) if device_days else None
        last_day = max(device_days) if device_days else None
        period_days = (date_to - date_from).days + 1

        return {
            "device_id": device_id,
            "device_name": device.name,
            "date_from": date_from,
            "date_to": date_to,
            "total_kwh": summary["total_kwh"],
            "avg_daily_kwh": summary["avg_daily_kwh"],
            "max_daily_kwh": summary["max_daily_kwh"],
            "max_daily_date": summary["max_daily_date"],
            "min_daily_kwh": summary["min_daily_kwh"],
            "min_daily_date": summary["min_daily_date"],
            "estimated_cost": period_cost.cost if period_cost else None,
            "cost_incomplete": period_cost.cost_incomplete if period_cost else False,
            "days_without_rate": period_cost.days_without_rate if period_cost else 0,
            "first_recorded_day": first_day,
            "last_recorded_day": last_day,
            "days_with_data": summary["days_with_data"],
            "days_without_data": period_days - summary["days_with_data"],
        }
