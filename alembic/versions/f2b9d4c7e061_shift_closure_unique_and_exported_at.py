"""Cierre de turno: un cierre por vendedor y día + exported_at

Revision ID: f2b9d4c7e061
Revises: e4a7c2d9b815
Create Date: 2026-10-15 23:45:00

El cierre de turno lo genera la exportación (no un CRUD): reexportar el mismo día
actualiza la fila de cada vendedor en lugar de duplicarla.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2b9d4c7e061"
down_revision: str | Sequence[str] | None = "e4a7c2d9b815"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "shift_closure",
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_shift_closure_date_vehicle",
        "shift_closure",
        ["closure_date", "id_user_vehicle"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_shift_closure_date_vehicle", "shift_closure", type_="unique")
    op.drop_column("shift_closure", "exported_at")
