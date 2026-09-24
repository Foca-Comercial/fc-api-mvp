from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.order import Order
    from app.models.coreModule.product import Product


class OrderDetail(Base):
    __tablename__ = "order_detail"
    __table_args__ = (
        CheckConstraint("cant > 0", name="chk_order_detail_cant"),
        CheckConstraint("unit_price >= 0", name="chk_order_detail_unit_price"),
        CheckConstraint("subtotal >= 0", name="chk_order_detail_subtotal"),
        Index("idx_order_detail_order", "id_order"),
        Index("idx_order_detail_product", "id_product"),
    )

    id_order_detail: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    cant: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Claves Foraneas
    id_order: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sale_order.id_order", ondelete="CASCADE"),
        nullable=False,
    )
    order: Mapped["Order"] = relationship(back_populates="order_details")

    id_product: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("product.id_product", ondelete="RESTRICT"),
        nullable=False,
    )
    product: Mapped["Product"] = relationship(back_populates="order_details")
