"""Archivado mensual: tablas monthly_archive y archive_spreadsheet

Revision ID: e4a7c2d9b815
Revises: d1e8b3f6a274
Create Date: 2026-10-15 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4a7c2d9b815"
down_revision: str | Sequence[str] | None = "d1e8b3f6a274"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "archive_spreadsheet",
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("spreadsheet_id", sa.String(length=100), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "year BETWEEN 2020 AND 2100", name="chk_archive_spreadsheet_year"
        ),
        sa.PrimaryKeyConstraint("year"),
    )
    op.create_table(
        "monthly_archive",
        sa.Column("archive_month", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "EXPORTED",
                "PURGED",
                name="chk_monthly_archive_status",
                native_enum=False,
                length=20,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("spreadsheet_id", sa.String(length=100), nullable=False),
        sa.Column("sheet_title", sa.String(length=20), nullable=False),
        sa.Column("orders_count", sa.Integer(), nullable=False),
        sa.Column("rows_count", sa.Integer(), nullable=False),
        sa.Column("total_sales", sa.Numeric(14, 2), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_user_exported", sa.BigInteger(), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id_user_purged", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM archive_month) = 1", name="chk_monthly_archive_month"
        ),
        sa.CheckConstraint(
            "orders_count >= 0 AND rows_count >= 0",
            name="chk_monthly_archive_counts",
        ),
        sa.ForeignKeyConstraint(
            ["id_user_exported"], ["app_user.id_user"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["id_user_purged"], ["app_user.id_user"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("archive_month"),
    )


def downgrade() -> None:
    op.drop_table("monthly_archive")
    op.drop_table("archive_spreadsheet")
