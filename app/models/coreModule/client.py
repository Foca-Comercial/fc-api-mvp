from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.client_route import ClientRoute
    from app.models.coreModule.order import Order
    from app.models.coreModule.special_customer_price import SpecialCustomerPrice
    from app.models.parametersModule.neighborhood import Neighborhood


class Client(Base):
    __tablename__ = "client"
    __table_args__ = (
        Index("idx_client_neighborhood", "id_neighborhood"),
        # Un cliente temporal (creado desde el pedido) siempre factura POS
        CheckConstraint(
            "is_registered OR NOT requires_electronic_invoice",
            name="chk_client_electronic_invoice_registered",
        ),
    )

    id_client: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(10), nullable=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Se le hace factura electrónica (informativo, como los precios pactados): sus
    # pedidos nacen con invoice_type = ELECTRONIC
    requires_electronic_invoice: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )

    # Claves Foraneas
    id_neighborhood: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("neighborhood.id_neighborhood", ondelete="RESTRICT"),
        nullable=False,
    )
    neighborhood: Mapped["Neighborhood"] = relationship(back_populates="clients")

    # PNI
    special_prices: Mapped[list["SpecialCustomerPrice"]] = relationship(
        back_populates="client"
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="client")
    client_routes: Mapped[list["ClientRoute"]] = relationship(back_populates="client")
