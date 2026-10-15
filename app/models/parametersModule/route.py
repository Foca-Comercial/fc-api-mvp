from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, SmallInteger, String, Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.client_route import ClientRoute
    from app.models.coreModule.order import Order


class Route(Base):
    __tablename__ = "route"
    __table_args__ = (
        # Al menos un día, y solo valores 1..7 (DayWeek: 1 = lunes ... 7 = domingo)
        CheckConstraint(
            "cardinality(days_week) > 0 "
            "AND days_week <@ ARRAY[1, 2, 3, 4, 5, 6, 7]::smallint[]",
            name="chk_route_days_week",
        ),
    )

    id_route: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    # Días en que sale la ruta (valores de DayWeek). Se reemplaza la lista
    # completa al editar; no mutar en sitio (SQLAlchemy no detecta ese cambio).
    days_week: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger), nullable=False)
    departure_time: Mapped[time] = mapped_column(Time, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    client_routes: Mapped[list["ClientRoute"]] = relationship(back_populates="route")
    orders: Mapped[list["Order"]] = relationship(back_populates="route")
