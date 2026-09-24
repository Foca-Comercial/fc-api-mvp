from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.user_vehicle import UserVehicle


class Vehicle(Base):
    __tablename__ = "vehicle"

    id_vehicle: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # PNI
    user_vehicles: Mapped[list["UserVehicle"]] = relationship(back_populates="vehicle")
