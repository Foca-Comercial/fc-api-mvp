from typing import TYPE_CHECKING

from sqlalchemy import CHAR, BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.order import Order
    from app.models.coreModule.shift_closure import ShiftClosure
    from app.models.parametersModule.vehicle import Vehicle
    from app.models.securityModule.user_role import UserRole


class UserVehicle(Base):
    __tablename__ = "user_vehicle"
    __table_args__ = (
        Index("idx_user_vehicle_user_role", "id_user_role"),
        Index("idx_user_vehicle_vehicle", "id_vehicle"),
    )

    id_user_vehicle: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    code: Mapped[str] = mapped_column(CHAR(2), nullable=False, unique=True)

    # Claves Foraneas
    id_user_role: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user_role.id_user_role", ondelete="RESTRICT"),
        nullable=False,
    )
    user_role: Mapped["UserRole"] = relationship(back_populates="user_vehicles")

    id_vehicle: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vehicle.id_vehicle", ondelete="RESTRICT"),
        nullable=False,
    )
    vehicle: Mapped["Vehicle"] = relationship(back_populates="user_vehicles")

    # PNI
    orders: Mapped[list["Order"]] = relationship(back_populates="user_vehicle")
    shift_closures: Mapped[list["ShiftClosure"]] = relationship(
        back_populates="user_vehicle"
    )
