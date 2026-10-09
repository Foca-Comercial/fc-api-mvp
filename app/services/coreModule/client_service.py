from sqlalchemy.orm import Session

from app.models.coreModule.client import Client
from app.repositories.coreModule.client_repository import client_repository
from app.repositories.parametersModule.neighborhood_repository import (
    neighborhood_repository,
)
from app.schemas.coreModule.client_schema import ClientCreate, ClientUpdate
from app.services.base_service import BaseService


class ClientService(BaseService[Client, ClientCreate, ClientUpdate]):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=client_repository, entity_name="Cliente")

    def search_by_name(self, db: Session, *, name: str) -> list[Client]:
        return self.repository.search_by_name(db, name=name)

    def _validate_before_create(self, db: Session, obj_in: ClientCreate) -> None:
        self._ensure_reference(
            db,
            neighborhood_repository,
            obj_in.id_neighborhood,
            field="id_neighborhood",
            label="Barrio",
        )

    def _validate_before_update(
        self, db: Session, obj_in: ClientUpdate, existing: Client
    ) -> None:
        if (
            obj_in.id_neighborhood is not None
            and obj_in.id_neighborhood != existing.id_neighborhood
        ):
            self._ensure_reference(
                db,
                neighborhood_repository,
                obj_in.id_neighborhood,
                field="id_neighborhood",
                label="Barrio",
            )


# Instancia única para inyectar en el router
client_service = ClientService()
