from app.models.parametersModule.route import Route
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.route_schema import RouteCreate, RouteUpdate


class RepositoryRoute(BaseRepository[Route, RouteCreate, RouteUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
route_repository = RepositoryRoute(Route)
