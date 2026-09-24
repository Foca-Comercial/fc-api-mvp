from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.user_vehicle import UserVehicle


class ShiftClosure(Base):
    __tablename__ = "shift_closure"
    __table_args__ = (
        CheckConstraint(
            "total_orders >= 0 AND total_sales >= 0", name="chk_shift_closure_totals"
        ),
        Index("idx_shift_closure_user_vehicle", "id_user_vehicle"),
    )

    id_shift_closure: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    closure_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    total_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    exported_siigo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Claves Foraneas
    id_user_vehicle: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user_vehicle.id_user_vehicle", ondelete="RESTRICT"),
        nullable=False,
    )
    user_vehicle: Mapped["UserVehicle"] = relationship(back_populates="shift_closures")
