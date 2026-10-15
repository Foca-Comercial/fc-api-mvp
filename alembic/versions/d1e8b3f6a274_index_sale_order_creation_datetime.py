"""Índice en sale_order.creation_datetime

Revision ID: d1e8b3f6a274
Revises: c7d4a1e9f256
Create Date: 2026-10-15 17:30:00

Los filtros por día y por mes (dashboard, rutas del día, histórico, archivado)
comparan creation_datetime contra un rango de instantes; este índice evita
recorrer la tabla completa.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d1e8b3f6a274"
down_revision: str | Sequence[str] | None = "c7d4a1e9f256"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "idx_sale_order_creation_datetime", "sale_order", ["creation_datetime"]
    )


def downgrade() -> None:
    op.drop_index("idx_sale_order_creation_datetime", table_name="sale_order")
