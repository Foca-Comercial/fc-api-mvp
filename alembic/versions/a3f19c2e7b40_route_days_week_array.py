"""Rutas con varios días: route.day_week -> route.days_week SMALLINT[]

Revision ID: a3f19c2e7b40
Revises: d907f08b264a
Create Date: 2026-10-14 22:30:00

Una ruta puede salir varios días de la semana (p. ej. lunes y jueves). Los datos
existentes se conservan: cada ruta pasa a tener una lista con su único día.

Downgrade: vuelve a un solo día y conserva el PRIMERO de la lista; los demás
días se pierden.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a3f19c2e7b40"
down_revision: str | Sequence[str] | None = "d907f08b264a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_CHECK = (
    "cardinality(days_week) > 0 "
    "AND days_week <@ ARRAY[1, 2, 3, 4, 5, 6, 7]::smallint[]"
)


def upgrade() -> None:
    op.add_column(
        "route",
        sa.Column("days_week", postgresql.ARRAY(sa.SmallInteger()), nullable=True),
    )
    op.execute("UPDATE route SET days_week = ARRAY[day_week]::smallint[]")
    op.alter_column("route", "days_week", nullable=False)

    op.drop_constraint("chk_route_day_week", "route", type_="check")
    op.drop_column("route", "day_week")
    op.create_check_constraint("chk_route_days_week", "route", NEW_CHECK)


def downgrade() -> None:
    op.add_column("route", sa.Column("day_week", sa.Integer(), nullable=True))
    op.execute("UPDATE route SET day_week = days_week[1]")
    op.alter_column("route", "day_week", nullable=False)

    op.drop_constraint("chk_route_days_week", "route", type_="check")
    op.drop_column("route", "days_week")
    op.create_check_constraint(
        "chk_route_day_week", "route", "day_week BETWEEN 1 AND 7"
    )
