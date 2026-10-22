from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.client_route_item import ClientRouteItem
from app.models.coreModule.product import Product
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.route_schema import RouteBaseItemInput


class RepositoryClientRouteItem(
    BaseRepository[ClientRouteItem, RouteBaseItemInput, RouteBaseItemInput]
):
    # Pedido base de varias asignaciones cliente-ruta, con código y nombre del
    # producto, en el orden en que se guardaron los renglones
    def get_for_links(self, db: Session, link_ids: list[int]) -> list[tuple]:
        if not link_ids:
            return []
        stmt = (
            select(
                ClientRouteItem.id_client_route,
                ClientRouteItem.id_product,
                Product.code.label("product_code"),
                Product.name.label("product_name"),
                ClientRouteItem.cant,
            )
            .join(Product, Product.id_product == ClientRouteItem.id_product)
            .where(ClientRouteItem.id_client_route.in_(link_ids))
            .order_by(ClientRouteItem.id_client_route_item)
        )
        return list(db.execute(stmt).all())

    # Pedido base de los clientes de una ruta, solo con productos activos (los que se
    # pueden pedir), para precargar el formulario de pedidos por ruta
    def get_for_route(self, db: Session, id_route: int) -> list[tuple]:
        stmt = (
            select(
                ClientRoute.id_client, ClientRouteItem.id_product, ClientRouteItem.cant
            )
            .join(
                ClientRoute,
                ClientRoute.id_client_route == ClientRouteItem.id_client_route,
            )
            .join(Product, Product.id_product == ClientRouteItem.id_product)
            .where(ClientRoute.id_route == id_route, Product.active.is_(True))
            .order_by(ClientRouteItem.id_client_route_item)
        )
        return list(db.execute(stmt).all())

    # Reemplaza el pedido base completo de una asignación cliente-ruta
    def replace(
        self, db: Session, *, id_client_route: int, items: list[RouteBaseItemInput]
    ) -> None:
        db.execute(
            delete(ClientRouteItem).where(
                ClientRouteItem.id_client_route == id_client_route
            )
        )
        for item in items:
            db.add(
                ClientRouteItem(
                    id_client_route=id_client_route,
                    id_product=item.id_product,
                    cant=item.cant,
                )
            )
        db.flush()


# Intancia del repositorio inyectando el modelo ORM
client_route_item_repository = RepositoryClientRouteItem(ClientRouteItem)
