from app.models.coreModule.client_route import ClientRoute
from app.repositories.coreModule.client_route_repository import client_route_repository
from app.schemas.coreModule.client_route_schema import (
    ClientRouteCreate,
    ClientRouteUpdate,
)
from app.services.base_service import BaseService


class ClientRouteService(
    BaseService[ClientRoute, ClientRouteCreate, ClientRouteUpdate]
):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=client_route_repository, entity_name="ClienteRuta")


# Instancia única para inyectar en el router
client_route_service = ClientRouteService()
