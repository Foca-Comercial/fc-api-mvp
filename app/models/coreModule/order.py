from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Time,
    func,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.utils.enums.order_state import OrderState

if TYPE_CHECKING:
    from app.models.coreModule.client import Client
    from app.models.coreModule.order_detail import OrderDetail
    from app.models.coreModule.user_vehicle import UserVehicle
    from app.models.parametersModule.route import Route
    from app.models.securityModule.user import User


class Order(Base):
    __tablename__ = "sale_order"
    __table_args__ = (
        CheckConstraint(
            "order_total IS NULL OR order_total >= 0", name="chk_order_total"
        ),
        Index("idx_sale_order_client", "id_client"),
        Index("idx_sale_order_user_vehicle", "id_user_vehicle"),
        Index("idx_sale_order_state", "state"),
        Index("idx_sale_order_user_taker", "id_user_taker"),
        Index("idx_sale_order_route", "id_route"),
        # Filtros por día/mes (dashboard, rutas del día, histórico, archivado)
        Index("idx_sale_order_creation_datetime", "creation_datetime"),
        # Día en que se atiende el pedido: tablero, rutas, cierre, archivado
        Index("idx_sale_order_delivery_date", "delivery_date"),
    )

    id_order: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    purchase_order: Mapped[str] = mapped_column(String(3), nullable=False)
    creation_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Día en que se atiende el pedido (hora de Bogotá). Normalmente es el día de
    # creación; un pedido programado lo trae en el futuro. Es el "día" del tablero,
    # el cierre, el consecutivo y el archivado; creation_datetime queda como
    # marca real de cuándo se tomó el pedido.
    delivery_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=text("(timezone('America/Bogota', now()))::date"),
    )
    estimated_delivery: Mapped[time | None] = mapped_column(Time, nullable=True)
    dispatch_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    delivery_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    state: Mapped[OrderState] = mapped_column(
        SQLEnum(
            OrderState,
            name="chk_order_state",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=OrderState.PENDING,
    )
    order_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Claves Foraneas
    id_client: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("client.id_client", ondelete="RESTRICT"), nullable=False
    )
    client: Mapped["Client"] = relationship(back_populates="orders")

    id_user_vehicle: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user_vehicle.id_user_vehicle", ondelete="RESTRICT"),
        nullable=True,
    )
    user_vehicle: Mapped["UserVehicle | None"] = relationship(back_populates="orders")

    id_user_taker: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("app_user.id_user", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_taker: Mapped["User"] = relationship(
        "User", foreign_keys=[id_user_taker], back_populates="orders"
    )

    # Ruta de la que se generó el pedido (None = pedido tomado individualmente)
    id_route: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("route.id_route", ondelete="RESTRICT"),
        nullable=True,
    )
    route: Mapped["Route | None"] = relationship(back_populates="orders")

    # PNI
    order_details: Mapped[list["OrderDetail"]] = relationship(back_populates="order")
