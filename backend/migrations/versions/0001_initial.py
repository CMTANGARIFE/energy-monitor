"""Esquema inicial: devices, energy_consumption, energy_rates, import_history

- UNIQUE(device_id, date) en energy_consumption (clave lógica del UPSERT)
- CHECK kwh >= 0
- Índices por device_id y date

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image", sa.String(255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_devices_name", "devices", ["name"], unique=True)

    op.create_table(
        "energy_consumption",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(),
                  sa.ForeignKey("devices.id", ondelete="RESTRICT", name="fk_energy_consumption_device_id_devices"),
                  nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("kwh", sa.Numeric(12, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("device_id", "date", name="uq_energy_consumption_device_date"),
        sa.CheckConstraint("kwh >= 0", name="ck_energy_consumption_kwh_non_negative"),
    )
    op.create_index("ix_energy_consumption_device_id", "energy_consumption", ["device_id"])
    op.create_index("ix_energy_consumption_date", "energy_consumption", ["date"])

    op.create_table(
        "energy_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("price_per_kwh", sa.Numeric(14, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_energy_rates_start_date", "energy_rates", ["start_date"])
    op.create_index("ix_energy_rates_end_date", "energy_rates", ["end_date"])

    op.create_table(
        "import_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(),
                  sa.ForeignKey("devices.id", ondelete="SET NULL", name="fk_import_history_device_id_devices"),
                  nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("records_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_ignored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("error_summary", sa.Text(), nullable=True),
    )
    op.create_index("ix_import_history_device_id", "import_history", ["device_id"])
    op.create_index("ix_import_history_imported_at", "import_history", ["imported_at"])


def downgrade() -> None:
    op.drop_table("import_history")
    op.drop_table("energy_rates")
    op.drop_table("energy_consumption")
    op.drop_table("devices")
