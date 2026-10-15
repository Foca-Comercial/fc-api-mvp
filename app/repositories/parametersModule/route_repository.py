from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.route import Route
from app.models.parametersModule.zone import Zone
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.route_schema import RouteCreate, RouteUpdate


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
                and_(Client.id_client == ClientRoute.id_client, Client.active.is_(True)),
            )
            .group_by(Route.id_route)
            .order_by(Route.name)
        )
        if only_active:
            stmt = stmt.where(Route.active.is_(True))
        return list(db.execute(stmt).all())

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


# Intancia del repositorio inyectando el modelo ORM
route_repository = RepositoryRoute(Route)
