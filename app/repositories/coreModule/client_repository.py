from app.models.coreModule.client import Client
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.client_schema import ClientCreate, ClientUpdate


class RepositoryClient(BaseRepository[Client, ClientCreate, ClientUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
client_repository = RepositoryClient(Client)
