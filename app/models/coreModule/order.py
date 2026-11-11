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
    and_,
    func,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import ColumnElement

from app.db.database import Base
from app.utils.enums.cancel_reason import CancelReason
from app.utils.enums.invoice_type import InvoiceType
from app.utils.enums.order_state import OrderState
from app.utils.enums.payment_method import PaymentMethod


def _text_enum(enum_cls, length: int) -> SQLEnum:
    """Enum guardado como VARCHAR (sin tipo ENUM nativo). El CHECK de valores se
    declara explícito en __table_args__ (y en la migración)."""
    return SQLEnum(
        enum_cls,
        native_enum=False,
        create_constraint=False,
        length=length,
        values_callable=lambda members: [m.value for m in members],
    )

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
        CheckConstraint(
            "payment_method IN ('CASH', 'TRANSFER', 'CREDIT')",
            name="chk_order_payment_method",
        ),
        CheckConstraint(
            "invoice_type IN ('POS', 'ELECTRONIC')", name="chk_order_invoice_type"
        ),
        CheckConstraint(
            "cancel_reason IS NULL OR cancel_reason IN "
            "('WRONG_BILLING', 'CLIENT_ABSENT', 'DAMAGED_PRODUCT', 'OTHER')",
            name="chk_order_cancel_reason_value",
        ),
        # Todo pedido cancelado tiene motivo, y solo los cancelados lo tienen
        CheckConstraint(
            "(state = 'CANCELLED') = (cancel_reason IS NOT NULL)",
            name="chk_order_cancel_reason",
        ),
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

    # Facturación: cómo paga y qué factura lleva. El tipo de factura se copia del
    # cliente al crear el pedido (un cambio posterior en el cliente no lo altera).
    payment_method: Mapped[PaymentMethod] = mapped_column(
        _text_enum(PaymentMethod, 20),
        nullable=False,
        default=PaymentMethod.CASH,
        server_default=PaymentMethod.CASH.value,
    )
    invoice_type: Mapped[InvoiceType] = mapped_column(
        _text_enum(InvoiceType, 20),
        nullable=False,
        default=InvoiceType.POS,
        server_default=InvoiceType.POS.value,
    )
    observations: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Cancelación (solo con state = CANCELLED; ver chk_order_cancel_reason)
    cancel_reason: Mapped[CancelReason | None] = mapped_column(
        _text_enum(CancelReason, 30), nullable=True
    )
    cancel_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Última edición de los productos del pedido (PUT /orders/{id}/items-order)
    items_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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

    id_user_canceller: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("app_user.id_user", ondelete="RESTRICT"),
        nullable=True,
    )
    user_canceller: Mapped["User | None"] = relationship(
        "User", foreign_keys=[id_user_canceller]
    )

    id_user_items_updater: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("app_user.id_user", ondelete="RESTRICT"),
        nullable=True,
    )
    user_items_updater: Mapped["User | None"] = relationship(
        "User", foreign_keys=[id_user_items_updater]
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

    # Regla única "lleva CD": solo POS + efectivo genera comprobante de despacho y
    # entra al consolidado del cierre. Sirve en Python (order.has_receipt) y en
    # SQL (select(Order.has_receipt) / .where(Order.has_receipt)).
    @hybrid_property
    def has_receipt(self) -> bool:
        return (
            self.payment_method == PaymentMethod.CASH
            and self.invoice_type == InvoiceType.POS
        )

    @has_receipt.inplace.expression
    @classmethod
    def _has_receipt_expression(cls) -> ColumnElement[bool]:
        return and_(
            cls.payment_method == PaymentMethod.CASH,
            cls.invoice_type == InvoiceType.POS,
        )
