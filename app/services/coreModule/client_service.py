from app.models.coreModule.client import Client
from app.repositories.coreModule.client_repository import client_repository
from app.schemas.coreModule.client_schema import ClientCreate, ClientUpdate
from app.services.base_service import BaseService


class ClientService(BaseService[Client, ClientCreate, ClientUpdate]):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=client_repository, entity_name="Cliente")


# Instancia única para inyectar en el router
client_service = ClientService()
