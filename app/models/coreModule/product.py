from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, BigInteger, Boolean, CheckConstraint, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.order_detail import OrderDetail
    from app.models.coreModule.special_customer_price import SpecialCustomerPrice


class Product(Base):
    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint("base_price >= 0", name="chk_product_base_price"),
    )

    id_product: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    code: Mapped[str] = mapped_column(CHAR(3), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # PNI
    special_prices: Mapped[list["SpecialCustomerPrice"]] = relationship(
        back_populates="product"
    )
    order_details: Mapped[list["OrderDetail"]] = relationship(back_populates="product")
