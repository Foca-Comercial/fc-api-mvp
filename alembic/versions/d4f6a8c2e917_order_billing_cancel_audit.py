"""Pago, factura, observación, cancelación y auditoría del pedido

Revision ID: d4f6a8c2e917
Revises: b7e2f4a9c1d3
Create Date: 2026-11-11 16:00:00

Base de los cambios finales (documento "Cambios finales — Foca Comercial", B1):

- sale_order: método de pago y tipo de factura (los pedidos existentes quedan
  como efectivo + POS, que es como funcionaban), observación general, datos de
  la cancelación (motivo, nota, cuándo y quién) y quién editó los productos por
  última vez y cuándo.
- client: marca de factura electrónica (solo clientes registrados).
- shift_closure: huella de los pedidos exportados, para detectar cualquier cambio
  posterior (también de método de pago o tipo de factura).

Los valores de los enums van como texto: una migración no importa nada que
pueda cambiar después.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4f6a8c2e917"
down_revision: str | Sequence[str] | None = "b7e2f4a9c1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHECKS = {
    "chk_order_payment_method": "payment_method IN ('CASH', 'TRANSFER', 'CREDIT')",
    "chk_order_invoice_type": "invoice_type IN ('POS', 'ELECTRONIC')",
    "chk_order_cancel_reason_value": (
        "cancel_reason IS NULL OR cancel_reason IN "
        "('WRONG_BILLING', 'CLIENT_ABSENT', 'DAMAGED_PRODUCT', 'OTHER')"
    ),
    "chk_order_cancel_reason": "(state = 'CANCELLED') = (cancel_reason IS NOT NULL)",
}
USER_FKS = {
    "sale_order_id_user_canceller_fkey": "id_user_canceller",
    "sale_order_id_user_items_updater_fkey": "id_user_items_updater",
}


def upgrade() -> None:
    # --- sale_order -----------------------------------------------------------
    op.add_column(
        "sale_order",
        sa.Column(
            "payment_method", sa.String(20), nullable=False, server_default="CASH"
        ),
    )
    op.add_column(
        "sale_order",
        sa.Column("invoice_type", sa.String(20), nullable=False, server_default="POS"),
    )
    op.add_column("sale_order", sa.Column("observations", sa.String(500)))
    op.add_column("sale_order", sa.Column("cancel_reason", sa.String(30)))
    op.add_column("sale_order", sa.Column("cancel_note", sa.String(300)))
    op.add_column("sale_order", sa.Column("cancelled_at", sa.DateTime(timezone=True)))
    op.add_column("sale_order", sa.Column("id_user_canceller", sa.BigInteger()))
    op.add_column(
        "sale_order", sa.Column("items_updated_at", sa.DateTime(timezone=True))
    )
    op.add_column("sale_order", sa.Column("id_user_items_updater", sa.BigInteger()))
    for name, column in USER_FKS.items():
        op.create_foreign_key(
            name, "sale_order", "app_user", [column], ["id_user"], ondelete="RESTRICT"
        )

    # Pedidos cancelados antes de existir el motivo
    op.execute("UPDATE sale_order SET cancel_reason = 'OTHER' WHERE state = 'CANCELLED'")
    for name, condition in CHECKS.items():
        op.create_check_constraint(name, "sale_order", condition)

    # --- client ---------------------------------------------------------------
    op.add_column(
        "client",
        sa.Column(
            "requires_electronic_invoice",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_check_constraint(
        "chk_client_electronic_invoice_registered",
        "client",
        "is_registered OR NOT requires_electronic_invoice",
    )

    # --- shift_closure --------------------------------------------------------
    op.add_column("shift_closure", sa.Column("signature", sa.CHAR(64)))


def downgrade() -> None:
    op.drop_column("shift_closure", "signature")

    op.drop_constraint(
        "chk_client_electronic_invoice_registered", "client", type_="check"
    )
    op.drop_column("client", "requires_electronic_invoice")

    for name in CHECKS:
        op.drop_constraint(name, "sale_order", type_="check")
    for name in USER_FKS:
        op.drop_constraint(name, "sale_order", type_="foreignkey")
    for column in (
        "id_user_items_updater",
        "items_updated_at",
        "id_user_canceller",
        "cancelled_at",
        "cancel_note",
        "cancel_reason",
        "observations",
        "invoice_type",
        "payment_method",
    ):
        op.drop_column("sale_order", column)
