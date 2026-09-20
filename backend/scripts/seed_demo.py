"""Carga de datos de demostración (sección 49).

SEPARADO de los datos reales: nunca se ejecuta automáticamente.
Uso (backend activo, p. ej. dentro del contenedor):

    python scripts/seed_demo.py                       # crea dispositivos demo + consumos + tarifas
    python scripts/seed_demo.py --force               # limpia datos demo antes de cargar

Los dispositivos demo se identifican por el prefijo [DEMO] en su nombre.
"""
from __future__ import annotations

import argparse
import datetime as dt
import random
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.session import SessionLocal  # noqa: E402
from app.models import Device, EnergyConsumption, EnergyRate, ImportHistory  # noqa: E402
from app.repositories.consumption import ConsumptionRepository  # noqa: E402
from app.services.importer import ImportService  # noqa: E402
from app.services.rates import RateService  # noqa: E402


DEMO_DEVICES = [
    ("[DEMO] PC Principal", "Computador de escritorio de uso diario"),
    ("[DEMO] Servidor", "Servidor casero encendido 24/7"),
    ("[DEMO] Nevera", "Refrigerador de cocina"),
    ("[DEMO] TV", "Televisor de la sala"),
]

DEMO_RATES = [
    (dt.date(2025, 11, 1), dt.date(2026, 1, 31), Decimal("780.00")),
    (dt.date(2026, 2, 1), dt.date(2026, 5, 31), Decimal("850.00")),
    (dt.date(2026, 6, 1), None, Decimal("920.00")),
]

# Consumo típico diario (kWh) para simular cada dispositivo
DEMO_PROFILES = {
    "[DEMO] PC Principal": (0.4, 3.5),
    "[DEMO] Servidor": (0.8, 1.6),
    "[DEMO] Nevera": (0.9, 2.2),
    "[DEMO] TV": (0.1, 1.8),
}


def clear_demo(db) -> int:
    """Elimina dispositivos demo y sus consumos (los reales nunca se tocan)."""
    demo = db.query(Device).filter(Device.name.like("[DEMO]%")).all()
    count = 0
    for device in demo:
        db.query(EnergyConsumption).filter(EnergyConsumption.device_id == device.id).delete()
        db.query(ImportHistory).filter(ImportHistory.device_id == device.id).delete()
        db.delete(device)
        count += 1
    db.commit()
    return count


def seed(db) -> None:
    # Tarifas demo (solo si no existen tarifas reales)
    existing_rates = db.query(EnergyRate).count()
    if existing_rates == 0:
        for start, end, price in DEMO_RATES:
            RateService(db).create(start, end, price)
        print(f"  + {len(DEMO_RATES)} tarifas demo creadas")

    rng = random.Random(42)  # determinista
    start_date = dt.date(2026, 1, 1)
    end_date = dt.date.today() - dt.timedelta(days=1)
    if end_date <= start_date:
        end_date = start_date + dt.timedelta(days=120)

    for name, description in DEMO_DEVICES:
        device = Device(name=name, description=description, active=True)
        db.add(device)
        db.commit()
        db.refresh(device)

        low, high = DEMO_PROFILES[name]
        rows = []
        day = start_date
        while day <= end_date:
            weekend_factor = 1.25 if day.weekday() >= 5 else 1.0
            kwh = round(rng.uniform(low, high) * weekend_factor, 2)
            rows.append({"date": day, "kwh": kwh})
            day += dt.timedelta(days=1)

        ConsumptionRepository(db).upsert_many(device.id, rows)
        db.add(ImportHistory(
            device_id=device.id,
            filename="demo_seed.csv",
            records_found=len(rows),
            records_inserted=len(rows),
            records_updated=0,
            records_ignored=0,
            status="success",
        ))
        db.commit()
        print(f"  + {name}: {len(rows)} días de consumo "
              f"({start_date.isoformat()} a {end_date.isoformat()})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cargar datos de demostración de Energy Monitor")
    parser.add_argument("--force", action="store_true",
                        help="elimina los datos demo existentes antes de cargar")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.force:
            removed = clear_demo(db)
            print(f"Datos demo previos eliminados: {removed} dispositivo(s).")
        if db.query(Device).filter(Device.name.like("[DEMO]%")).count() > 0:
            print("Ya existen datos demo. Use --force para recargarlos.")
            return
        print("Cargando datos de demostración...")
        seed(db)
        print("Datos demo cargados correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
