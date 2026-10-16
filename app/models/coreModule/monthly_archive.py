from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.utils.enums.archive_status import ArchiveStatus


class MonthlyArchive(Base):
    """Bitácora del archivado mensual: una fila por mes exportado/purgado.

    Hace el proceso auditable e idempotente: reexportar un mes actualiza su fila;
    purgarlo la deja en PURGED.
    """

    __tablename__ = "monthly_archive"
    __table_args__ = (
        CheckConstraint(
            "EXTRACT(DAY FROM archive_month) = 1", name="chk_monthly_archive_month"
        ),
        CheckConstraint(
            "orders_count >= 0 AND rows_count >= 0", name="chk_monthly_archive_counts"
        ),
    )

    # Primer día del mes archivado (2026-09-01 = septiembre de 2026)
    archive_month: Mapped[date] = mapped_column(Date, primary_key=True)
    status: Mapped[ArchiveStatus] = mapped_column(
        SQLEnum(
            ArchiveStatus,
            name="chk_monthly_archive_status",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    spreadsheet_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sheet_title: Mapped[str] = mapped_column(String(20), nullable=False)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_sales: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    exported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    id_user_exported: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("app_user.id_user", ondelete="SET NULL"), nullable=True
    )
    purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    id_user_purged: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("app_user.id_user", ondelete="SET NULL"), nullable=True
    )
