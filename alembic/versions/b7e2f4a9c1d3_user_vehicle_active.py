"""Estado (active) en user_vehicle: asignaciones domiciliario-vehículo

Revision ID: b7e2f4a9c1d3
Revises: a9c3e7b1d584
Create Date: 2026-10-28 23:00:00

Una asignación (domiciliario + vehículo, con su código de vendedor para Siigo) no se
puede borrar si ya tiene pedidos o cierres. Con `active` se retira sin perder el
historial: deja de ofrecerse al asignar pedidos. Las asignaciones existentes quedan
activas.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7e2f4a9c1d3"
down_revision: str | Sequence[str] | None = "a9c3e7b1d584"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_vehicle",
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("user_vehicle", "active")
