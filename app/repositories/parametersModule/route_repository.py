from sqlalchemy import and_, any_, exists, func, select
from sqlalchemy.orm import Session

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.order import Order
from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.route import Route
from app.models.parametersModule.zone import Zone
from app.repositories.base_repository import BaseRepository
from app.repositories.time_filters import on_bogota_day
from app.schemas.parametersModule.route_schema import RouteCreate, RouteUpdate
from app.utils.enums.order_state import OrderState


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
                on_bogota_day(Order.creation_datetime, orders_date),
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


# Intancia del repositorio inyectando el modelo ORM
route_repository = RepositoryRoute(Route)
