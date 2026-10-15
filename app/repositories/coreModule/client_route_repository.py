from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coreModule.client_route import ClientRoute
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.client_route_schema import (
    ClientRouteCreate,
    ClientRouteUpdate,
)


class RepositoryClientRoute(
    BaseRepository[ClientRoute, ClientRouteCreate, ClientRouteUpdate]
):
    def get_by_pair(
        self, db: Session, *, id_route: int, id_client: int
    ) -> ClientRoute | None:
        stmt = select(ClientRoute).where(
            ClientRoute.id_route == id_route, ClientRoute.id_client == id_client
        )
        return db.scalars(stmt).first()


# Intancia del repositorio inyectando el modelo ORM
client_route_repository = RepositoryClientRoute(ClientRoute)
