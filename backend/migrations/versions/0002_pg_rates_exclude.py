"""Restricción EXCLUDE anti-solapamiento de tarifas (solo PostgreSQL)

Refuerza a nivel de base de datos la regla de negocio: los periodos de
tarifas no pueden solaparse (usa btree_gist + daterange &&).
El NULL en end_date se representa como [start, ∞).

Nota: si la extensión btree_gist no está disponible en la instalación,
la restricción se omite de forma segura: la regla sigue aplicándose a
nivel de servicio (app/services/rates.py) y los tests la verifican.

Revision ID: 0002_pg_rates_exclude
Revises: 0001_initial
Create Date: 2026-01-01
"""
import logging

from alembic import op
import sqlalchemy as sa

revision = "0002_pg_rates_exclude"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ex_energy_rates_no_overlap"
logger = logging.getLogger("alembic.energy_monitor")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (tests/desarrollo ligero) no soporta EXCLUDE;
        # la regla se aplica a nivel de servicio.
        return

    # Intentar habilitar btree_gist sin romper la migración si no existe
    try:
        bind.execute(sa.text("SAVEPOINT em_btree_gist"))
        bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        bind.execute(sa.text("RELEASE SAVEPOINT em_btree_gist"))
    except Exception as exc:  # noqa: BLE001
        bind.execute(sa.text("ROLLBACK TO SAVEPOINT em_btree_gist"))
        logger.warning(
            "btree_gist no disponible (%s): se omite la restricción EXCLUDE de tarifas. "
            "La regla anti-solapamiento sigue aplicándose a nivel de aplicación.", exc
        )
        return

    op.execute(
        f"""
        ALTER TABLE energy_rates
        ADD CONSTRAINT {CONSTRAINT_NAME}
        EXCLUDE USING gist (
            daterange(start_date,
                      CASE WHEN end_date IS NULL THEN NULL::date
                           ELSE (end_date + INTERVAL '1 day')::date END,
                      '[]')
            WITH &&
        )
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(f"ALTER TABLE energy_rates DROP CONSTRAINT IF EXISTS {CONSTRAINT_NAME}")
