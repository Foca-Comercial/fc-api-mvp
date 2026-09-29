from app.models.parametersModule.neighborhood import Neighborhood
from app.repositories.parametersModule.neighborhood_repository import (
    neighborhood_repository,
)
from app.schemas.parametersModule.neighborhood_schema import (
    NeighborhoodCreate,
    NeighborhoodUpdate,
)
from app.services.base_service import BaseService


class NeighborhoodService(
    BaseService[Neighborhood, NeighborhoodCreate, NeighborhoodUpdate]
):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=neighborhood_repository, entity_name="Barrio")


# Instancia única para inyectar en el router
neighborhood_service = NeighborhoodService()
