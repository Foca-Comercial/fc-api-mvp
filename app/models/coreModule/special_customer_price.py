from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.client import Client
    from app.models.coreModule.product import Product


class SpecialCustomerPrice(Base):
    __tablename__ = "special_customer_price"
    __table_args__ = (
        UniqueConstraint(
            "id_client", "id_product", name="uq_special_price_client_product"
        ),
        CheckConstraint("agreed_price >= 0", name="chk_special_price_agreed"),
        Index("idx_special_price_client", "id_client"),
        Index("idx_special_price_product", "id_product"),
    )

    id_client_price: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    agreed_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Claves Foraneas
    id_client: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("client.id_client", ondelete="CASCADE"), nullable=False
    )
    client: Mapped["Client"] = relationship(back_populates="special_prices")

    id_product: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id_product", ondelete="CASCADE"), nullable=False
    )
    product: Mapped["Product"] = relationship(back_populates="special_prices")
