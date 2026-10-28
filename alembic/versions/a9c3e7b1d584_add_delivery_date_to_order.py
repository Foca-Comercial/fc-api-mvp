"""Fecha de entrega (día de atención) en sale_order

Revision ID: a9c3e7b1d584
Revises: f2b9d4c7e061
Create Date: 2026-10-28 09:00:00

Permite programar pedidos para días posteriores. El tablero, las rutas, el
consecutivo, el cierre y el archivado pasan a usar delivery_date en lugar del
día de creation_datetime. Los pedidos existentes quedan con el día de Bogotá en
que se crearon, así que su comportamiento no cambia.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9c3e7b1d584"
down_revision: str | Sequence[str] | None = "f2b9d4c7e061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BOGOTA_TODAY = "(timezone('America/Bogota', now()))::date"


def upgrade() -> None:
    # 1. Columna nullable, para poder rellenar los pedidos existentes
    op.add_column("sale_order", sa.Column("delivery_date", sa.Date(), nullable=True))
    # 2. Pedidos existentes: el día de Bogotá en que se crearon
    op.execute(
        "UPDATE sale_order "
        "SET delivery_date = (timezone('America/Bogota', creation_datetime))::date"
    )
    # 3. Obligatoria, con default en la BD (hoy en Bogotá) para cualquier insert
    op.alter_column(
        "sale_order",
        "delivery_date",
        nullable=False,
        server_default=sa.text(BOGOTA_TODAY),
    )
    op.create_index("idx_sale_order_delivery_date", "sale_order", ["delivery_date"])


def downgrade() -> None:
    op.drop_index("idx_sale_order_delivery_date", table_name="sale_order")
    op.drop_column("sale_order", "delivery_date")
