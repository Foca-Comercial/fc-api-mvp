from app.models.parametersModule.neighborhood import Neighborhood
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.neighborhood_schema import (
    NeighborhoodCreate,
    NeighborhoodUpdate,
)


class RepositoryNeighborhood(
    BaseRepository[Neighborhood, NeighborhoodCreate, NeighborhoodUpdate]
):
    pass


# Intancia del repositorio inyectando el modelo ORM
neighborhood_repository = RepositoryNeighborhood(Neighborhood)
