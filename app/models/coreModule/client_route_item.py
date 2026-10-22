from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.client_route import ClientRoute
    from app.models.coreModule.product import Product


class ClientRouteItem(Base):
    """Pedido base de un cliente en una ruta: un renglón (producto + cantidad).

    Es lo que el cliente suele pedir cada vez que sale la ruta. Precarga el formulario
    de pedidos por ruta (GET /orders/routes/{id}/template); el precio no se guarda
    aquí, se resuelve al generar el pedido (pactado o base).
    """

    __tablename__ = "client_route_item"
    __table_args__ = (
        CheckConstraint("cant > 0", name="chk_client_route_item_cant"),
        # Un producto aparece una sola vez en el pedido base
        UniqueConstraint("id_client_route", "id_product", name="uq_client_route_item"),
        Index("idx_client_route_item_link", "id_client_route"),
        Index("idx_client_route_item_product", "id_product"),
    )

    id_client_route_item: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    cant: Mapped[int] = mapped_column(Integer, nullable=False)

    # Claves Foraneas
    # Al quitar el cliente de la ruta se borra su pedido base
    id_client_route: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("client_route.id_client_route", ondelete="CASCADE"),
        nullable=False,
    )
    client_route: Mapped["ClientRoute"] = relationship(back_populates="items")

    id_product: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("product.id_product", ondelete="RESTRICT"),
        nullable=False,
    )
    product: Mapped["Product"] = relationship()
