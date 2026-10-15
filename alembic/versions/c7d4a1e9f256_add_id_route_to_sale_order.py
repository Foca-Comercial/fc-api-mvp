"""Pedidos por ruta: sale_order.id_route

Revision ID: c7d4a1e9f256
Revises: b5c2e8d1f093
Create Date: 2026-10-15 12:00:00

Guarda de qué ruta se generó cada pedido (NULL = pedido tomado individualmente).
Los pedidos existentes quedan con NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7d4a1e9f256"
down_revision: str | Sequence[str] | None = "b5c2e8d1f093"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sale_order", sa.Column("id_route", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "sale_order_id_route_fkey",
        "sale_order",
        "route",
        ["id_route"],
        ["id_route"],
        ondelete="RESTRICT",
    )
    op.create_index("idx_sale_order_route", "sale_order", ["id_route"])


def downgrade() -> None:
    op.drop_index("idx_sale_order_route", table_name="sale_order")
    op.drop_constraint("sale_order_id_route_fkey", "sale_order", type_="foreignkey")
    op.drop_column("sale_order", "id_route")
