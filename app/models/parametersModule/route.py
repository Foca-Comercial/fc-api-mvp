import enum
from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.client_route import ClientRoute


class DayWeek(enum.IntEnum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class Route(Base):
    __tablename__ = "route"
    __table_args__ = (
        CheckConstraint("day_week BETWEEN 1 AND 7", name="chk_route_day_week"),
    )

    id_route: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    day_week: Mapped[DayWeek] = mapped_column(Integer, nullable=False)
    departure_time: Mapped[time] = mapped_column(Time, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # PNI
    client_routes: Mapped[list["ClientRoute"]] = relationship(back_populates="route")
