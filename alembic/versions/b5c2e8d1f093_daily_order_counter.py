"""Consecutivo diario de pedidos: tabla daily_order_counter

Revision ID: b5c2e8d1f093
Revises: a3f19c2e7b40
Create Date: 2026-10-15 11:40:00

sale_order.purchase_order pasa a ser un consecutivo por día (hora de Bogotá) que
asigna el servidor. Esta tabla guarda el último número usado en cada día.

Se inicializa con la cantidad de pedidos que ya existen por día, para que el
siguiente número de hoy continúe después de los pedidos ya registrados. Los
pedidos existentes NO se renumeran: conservan su purchase_order.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b5c2e8d1f093"
down_revision: str | Sequence[str] | None = "a3f19c2e7b40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_order_counter",
        sa.Column("counter_date", sa.Date(), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False),
        sa.CheckConstraint("last_value > 0", name="chk_daily_order_counter_value"),
        sa.PrimaryKeyConstraint("counter_date"),
    )
    op.execute(
        """
        INSERT INTO daily_order_counter (counter_date, last_value)
        SELECT (creation_datetime AT TIME ZONE 'America/Bogota')::date, COUNT(*)
        FROM sale_order
        GROUP BY 1
        """
    )


def downgrade() -> None:
    op.drop_table("daily_order_counter")
