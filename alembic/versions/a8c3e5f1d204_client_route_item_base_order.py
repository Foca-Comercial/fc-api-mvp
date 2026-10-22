"""Pedido base por cliente de ruta: tabla client_route_item

Revision ID: a8c3e5f1d204
Revises: f2b9d4c7e061
Create Date: 2026-10-23 10:00:00

Cada cliente de una ruta puede tener un pedido base (productos + cantidades) que
precarga el formulario de pedidos por ruta. El precio no se guarda: se resuelve al
generar el pedido. Al quitar el cliente de la ruta, su pedido base se borra en cascada.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a8c3e5f1d204"
down_revision: str | Sequence[str] | None = "f2b9d4c7e061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_route_item",
        sa.Column(
            "id_client_route_item", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.Column("cant", sa.Integer(), nullable=False),
        sa.Column("id_client_route", sa.BigInteger(), nullable=False),
        sa.Column("id_product", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("cant > 0", name="chk_client_route_item_cant"),
        sa.ForeignKeyConstraint(
            ["id_client_route"], ["client_route.id_client_route"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["id_product"], ["product.id_product"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id_client_route_item"),
        sa.UniqueConstraint(
            "id_client_route", "id_product", name="uq_client_route_item"
        ),
    )
    op.create_index(
        "idx_client_route_item_link", "client_route_item", ["id_client_route"]
    )
    op.create_index(
        "idx_client_route_item_product", "client_route_item", ["id_product"]
    )


def downgrade() -> None:
    op.drop_index("idx_client_route_item_product", table_name="client_route_item")
    op.drop_index("idx_client_route_item_link", table_name="client_route_item")
    op.drop_table("client_route_item")
