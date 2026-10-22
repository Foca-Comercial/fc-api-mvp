from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.coreModule.client import Client
    from app.models.coreModule.client_route_item import ClientRouteItem
    from app.models.parametersModule.route import Route


class ClientRoute(Base):
    __tablename__ = "client_route"
    __table_args__ = (
        UniqueConstraint("id_client", "id_route", name="uq_client_route"),
        Index("idx_client_route_client", "id_client"),
        Index("idx_client_route_route", "id_route"),
    )

    id_client_route: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    # Claves Foraneas
    id_client: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("client.id_client", ondelete="CASCADE"), nullable=False
    )
    client: Mapped["Client"] = relationship(back_populates="client_routes")

    id_route: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("route.id_route", ondelete="CASCADE"), nullable=False
    )
    route: Mapped["Route"] = relationship(back_populates="client_routes")

    # Pedido base del cliente en esta ruta (lo borra la BD con ON DELETE CASCADE)
    items: Mapped[list["ClientRouteItem"]] = relationship(
        back_populates="client_route",
        passive_deletes=True,
        order_by="ClientRouteItem.id_client_route_item",
    )
