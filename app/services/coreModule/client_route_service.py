from app.models.coreModule.client_route import ClientRoute
from app.repositories.coreModule.client_repository import (
    client_repository,
)
from app.repositories.coreModule.client_route_repository import client_route_repository
from app.repositories.parametersModule.route_repository import (
    route_repository,
)
from app.schemas.coreModule.client_route_schema import (
    ClientRouteCreate,
    ClientRouteUpdate,
)
from app.services.base_service import BaseService
from app.services.validation import ReferenceRule, UniqueTogether


class ClientRouteService(
    BaseService[ClientRoute, ClientRouteCreate, ClientRouteUpdate]
):
    references = (
        ReferenceRule("id_client", "Cliente", client_repository),
        ReferenceRule("id_route", "Ruta", route_repository),
    )
    unique_together = (UniqueTogether("Cliente y ruta", ("id_client", "id_route")),)

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=client_route_repository, entity_name="ClienteRuta")


# Instancia única para inyectar en el router
client_route_service = ClientRouteService()
