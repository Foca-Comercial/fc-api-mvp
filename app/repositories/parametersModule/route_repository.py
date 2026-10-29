from typing import Any

from sqlalchemy import Select, and_, any_, exists, func, select
from sqlalchemy.orm import Session

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.order import Order
from app.models.coreModule.product import Product
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.route import Route
from app.models.parametersModule.zone import Zone
from app.repositories.base_repository import BaseRepository
from app.repositories.pagination import paginate
from app.schemas.common.page_schema import PageParams
from app.schemas.parametersModule.route_schema import (
    RouteAdminFilters,
    RouteCreate,
    RouteUpdate,
)
from app.utils.enums.order_state import OrderState


def _special_prices_count():
    """Productos ACTIVOS con precio especial del cliente (subconsulta por fila): los
    únicos que se le pueden pedir desde una ruta."""
    return (
        select(func.count(SpecialCustomerPrice.id_client_price))
        .join(Product, Product.id_product == SpecialCustomerPrice.id_product)
        .where(
            SpecialCustomerPrice.id_client == Client.id_client,
            Product.active.is_(True),
        )
        .correlate(Client)
        .scalar_subquery()
    )


class RepositoryRoute(BaseRepository[Route, RouteCreate, RouteUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Route]:
        stmt = select(self.model)

        if only_active:
            stmt = stmt.where(self.model.active.is_(True))

        stmt = (
            stmt.order_by(*[col.asc() for col in self._primary_key_columns])
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    # Cards de la vista de Rutas: cada ruta con su número de clientes activos
    def get_cards(self, db: Session, *, only_active: bool = False) -> list[tuple]:
        clients_count = func.count(Client.id_client).label("clients_count")
        stmt = (
            select(Route, clients_count)
            .outerjoin(ClientRoute, ClientRoute.id_route == Route.id_route)
            .outerjoin(
                Client,
                and_(
                    Client.id_client == ClientRoute.id_client, Client.active.is_(True)
                ),
            )
            .group_by(Route.id_route)
            .order_by(Route.name)
        )
        if only_active:
            stmt = stmt.where(Route.active.is_(True))
        return list(db.execute(stmt).all())

    # Nombres de los clientes activos y zonas de cada ruta, en UNA consulta para todas
    # (las cards los muestran sin pedir los clientes ruta por ruta).
    # {id_route: (nombres A-Z, zonas A-Z sin repetir)}. Las rutas sin clientes no
    # aparecen. `registered_only` replica el criterio de cada conteo: las rutas del día
    # cuentan solo clientes registrados; las cards, todos los activos.
    def get_clients_summary(
        self, db: Session, route_ids: list[int], *, registered_only: bool = False
    ) -> dict[int, tuple[list[str], list[str]]]:
        if not route_ids:
            return {}
        stmt = (
            select(
                ClientRoute.id_route,
                Client.name,
                Zone.name.label("zone_name"),
            )
            .join(Client, Client.id_client == ClientRoute.id_client)
            .join(Neighborhood, Neighborhood.id_neighborhood == Client.id_neighborhood)
            .join(Zone, Zone.id_zone == Neighborhood.id_zone)
            .where(ClientRoute.id_route.in_(route_ids), Client.active.is_(True))
            .order_by(ClientRoute.id_route, Client.name)
        )
        if registered_only:
            stmt = stmt.where(Client.is_registered.is_(True))

        summary: dict[int, tuple[list[str], list[str]]] = {}
        for row in db.execute(stmt).all():
            names, zones = summary.setdefault(row.id_route, ([], []))
            names.append(row.name)
            if row.zone_name not in zones:
                zones.append(row.zone_name)
        return {
            id_route: (names, sorted(zones))
            for id_route, (names, zones) in summary.items()
        }

    # Clientes asignados a una ruta, con barrio y zona para mostrarlos
    def get_clients(self, db: Session, id_route: int) -> list[tuple]:
        stmt = (
            select(
                ClientRoute.id_client_route,
                Client.id_client,
                Client.name,
                Client.phone,
                Client.address,
                Neighborhood.name.label("neighborhood_name"),
                Zone.name.label("zone_name"),
                Client.active,
                _special_prices_count().label("special_prices_count"),
            )
            .join(Client, Client.id_client == ClientRoute.id_client)
            .join(Neighborhood, Neighborhood.id_neighborhood == Client.id_neighborhood)
            .join(Zone, Zone.id_zone == Neighborhood.id_zone)
            .where(ClientRoute.id_route == id_route)
            .order_by(Client.name)
        )
        return list(db.execute(stmt).all())

    # Clientes que se pueden asignar: registrados, activos y aún no en esta ruta
    def get_available_clients(
        self, db: Session, id_route: int, *, name: str | None = None, limit: int = 20
    ) -> list[tuple]:
        already_assigned = exists().where(
            ClientRoute.id_client == Client.id_client,
            ClientRoute.id_route == id_route,
        )
        stmt = (
            select(
                Client.id_client,
                Client.name,
                Client.phone,
                Client.address,
                Neighborhood.name.label("neighborhood_name"),
                Zone.name.label("zone_name"),
                _special_prices_count().label("special_prices_count"),
            )
            .join(Neighborhood, Neighborhood.id_neighborhood == Client.id_neighborhood)
            .join(Zone, Zone.id_zone == Neighborhood.id_zone)
            .where(
                Client.active.is_(True),
                Client.is_registered.is_(True),
                ~already_assigned,
            )
            .order_by(Client.name)
            .limit(limit)
        )
        if name:
            stmt = stmt.where(Client.name.ilike(f"%{name}%"))
        return list(db.execute(stmt).all())

    # Clientes a los que se les toma pedido desde la ruta: activos y registrados
    def get_orderable_clients(self, db: Session, id_route: int) -> list[tuple]:
        stmt = (
            select(
                Client.id_client,
                Client.name,
                Client.phone,
                Client.address,
                Neighborhood.name.label("neighborhood_name"),
                Zone.name.label("zone_name"),
            )
            .join(ClientRoute, ClientRoute.id_client == Client.id_client)
            .join(Neighborhood, Neighborhood.id_neighborhood == Client.id_neighborhood)
            .join(Zone, Zone.id_zone == Neighborhood.id_zone)
            .where(
                ClientRoute.id_route == id_route,
                Client.active.is_(True),
                Client.is_registered.is_(True),
            )
            .order_by(Client.name)
        )
        return list(db.execute(stmt).all())

    # Rutas activas que salen el día `weekday` (1 = lunes ... 7 = domingo), con
    # sus clientes y los pedidos ya generados en `orders_date` (día de Bogotá).
    def get_routes_of_day(self, db: Session, weekday: int, orders_date) -> list[tuple]:
        clients_count = (
            select(func.count())
            .select_from(ClientRoute)
            .join(Client, Client.id_client == ClientRoute.id_client)
            .where(
                ClientRoute.id_route == Route.id_route,
                Client.active.is_(True),
                Client.is_registered.is_(True),
            )
            .correlate(Route)
            .scalar_subquery()
        )
        orders_count = (
            select(func.count())
            .select_from(Order)
            .where(
                Order.id_route == Route.id_route,
                Order.state != OrderState.CANCELLED,
                Order.delivery_date == orders_date,
            )
            .correlate(Route)
            .scalar_subquery()
        )
        stmt = (
            select(
                Route,
                clients_count.label("clients_count"),
                orders_count.label("orders_count"),
            )
            .where(Route.active.is_(True), weekday == any_(Route.days_week))  # type: ignore
            .order_by(Route.departure_time, Route.name)
        )
        return list(db.execute(stmt).all())

    # ------------------------------------------------------------------
    # Panel de administración
    # ------------------------------------------------------------------
    @staticmethod
    def _admin_conditions(filters: RouteAdminFilters) -> list[Any]:
        conditions: list[Any] = []
        if filters.search:
            conditions.append(Route.name.icontains(filters.search, autoescape=True))
        if filters.active is not None:
            conditions.append(Route.active.is_(filters.active))
        if filters.day is not None:
            conditions.append(int(filters.day) == any_(Route.days_week))
        return conditions

    @staticmethod
    def _admin_select() -> Select:
        # Clientes activos asignados (subconsulta: solo para las filas de la página)
        clients_count = (
            select(func.count(ClientRoute.id_client_route))
            .join(Client, Client.id_client == ClientRoute.id_client)
            .where(ClientRoute.id_route == Route.id_route, Client.active.is_(True))
            .correlate(Route)
            .scalar_subquery()
        )
        return select(
            Route.id_route,
            Route.name,
            Route.days_week,
            Route.departure_time,
            Route.active,
            clients_count.label("clients_count"),
        )

    # Una página de rutas, por nombre
    def get_admin_page(
        self, db: Session, filters: RouteAdminFilters, params: PageParams
    ) -> tuple[list[Any], int]:
        conditions = self._admin_conditions(filters)
        stmt = (
            self._admin_select()
            .where(*conditions)
            .order_by(Route.name, Route.id_route)
        )
        count_stmt = select(Route.id_route).where(*conditions)
        return paginate(db, stmt, params, count_stmt=count_stmt)

    def get_admin_row(self, db: Session, id_route: int) -> Any | None:
        stmt = self._admin_select().where(Route.id_route == id_route)
        return db.execute(stmt).one_or_none()


# Intancia del repositorio inyectando el modelo ORM
route_repository = RepositoryRoute(Route)
