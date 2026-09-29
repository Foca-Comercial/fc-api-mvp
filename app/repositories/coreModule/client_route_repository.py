from app.models.coreModule.client_route import ClientRoute
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.client_route_schema import (
    ClientRouteCreate,
    ClientRouteUpdate,
)


class RepositoryClientRoute(
    BaseRepository[ClientRoute, ClientRouteCreate, ClientRouteUpdate]
):
    pass


# Intancia del repositorio inyectando el modelo ORM
client_route_repository = RepositoryClientRoute(ClientRoute)
