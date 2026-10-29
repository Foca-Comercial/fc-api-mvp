from sqlalchemy.orm import Session

from app.models.coreModule.client import Client
from app.repositories.coreModule.client_repository import client_repository
from app.repositories.parametersModule.neighborhood_repository import (
    neighborhood_repository,
)
from app.schemas.common.page_schema import Page, PageParams
from app.schemas.coreModule.client_schema import (
    ClientAdminCreate,
    ClientAdminFilters,
    ClientAdminRow,
    ClientAdminUpdate,
    ClientCreate,
    ClientUpdate,
)
from app.services.base_service import BaseService
from app.utils.exceptions.business_exceptions import (
    BusinessValidationError,
    EntityNotFoundError,
)

# Campos del cliente que no pueden quedar en null al editar (columnas NOT NULL)
_REQUIRED_ON_UPDATE = {
    "name": "nombre",
    "id_neighborhood": "barrio",
    "active": "estado",
}


class ClientService(BaseService[Client, ClientCreate, ClientUpdate]):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=client_repository, entity_name="Cliente")

    # Buscar un cliente por su nombre
    def search_by_name(self, db: Session, *, name: str) -> list[Client]:
        return self.repository.search_by_name(db, name=name)

    def _validate_before_create(self, db: Session, obj_in: ClientCreate) -> None:
        self._ensure_neighborhood(db, obj_in.id_neighborhood)

    def _validate_before_update(
        self, db: Session, obj_in: ClientUpdate, existing: Client
    ) -> None:
        if (
            obj_in.id_neighborhood is not None
            and obj_in.id_neighborhood != existing.id_neighborhood
        ):
            self._ensure_neighborhood(db, obj_in.id_neighborhood)

    # ------------------------------------------------------------------
    # Panel de administración: solo clientes REGISTRADOS
    # ------------------------------------------------------------------
    def get_admin_page(
        self, db: Session, *, filters: ClientAdminFilters, params: PageParams
    ) -> Page[ClientAdminRow]:
        rows, total = client_repository.get_admin_page(db, filters, params)
        items = [
            ClientAdminRow.model_validate(row, from_attributes=True) for row in rows
        ]
        return Page[ClientAdminRow].build(items, total=total, params=params)

    def create_registered(
        self, db: Session, *, obj_in: ClientAdminCreate
    ) -> ClientAdminRow:
        """Crea un cliente registrado (persiste; los temporales se crean desde el
        pedido y los borra la purga)."""
        self._ensure_neighborhood(db, obj_in.id_neighborhood)
        client = client_repository.add(
            db, obj_in_data={**obj_in.model_dump(), "is_registered": True}
        )
        db.commit()
        return self._admin_row(db, client.id_client)

    def update_registered(
        self, db: Session, *, id_client: int, obj_in: ClientAdminUpdate
    ) -> ClientAdminRow:
        """PATCH parcial de un cliente registrado. `active=False` lo desactiva
        (deja de aparecer al tomar pedidos, en rutas y en la búsqueda; su
        historial se conserva) y `active=True` lo reactiva."""
        client = self.get_registered(db, id_client)

        sent = obj_in.model_fields_set
        for field, label in _REQUIRED_ON_UPDATE.items():
            if field in sent and getattr(obj_in, field) is None:
                raise BusinessValidationError(
                    f"El {label} del cliente no puede quedar vacío.",
                    field=field,
                    code="REQUIRED_FIELD",
                )
        if (
            obj_in.id_neighborhood is not None
            and obj_in.id_neighborhood != client.id_neighborhood
        ):
            self._ensure_neighborhood(db, obj_in.id_neighborhood)

        self.repository.update(db, db_obj=client, obj_in=obj_in)
        return self._admin_row(db, id_client)

    def get_registered(self, db: Session, id_client: int) -> Client:
        """Cliente gestionable en el panel: 404 si no existe, 422 si es temporal.
        Lo usan también los precios especiales del cliente."""
        client = self.get(db, id_client)
        if not client.is_registered:
            raise BusinessValidationError(
                "Este cliente es temporal (se creó desde un pedido) y no se gestiona "
                "en el panel; se elimina con la purga mensual.",
                field="id_client",
                code="CLIENT_NOT_REGISTERED",
            )
        return client

    # --- Utilidades ---

    def _ensure_neighborhood(self, db: Session, id_neighborhood: int) -> None:
        self._ensure_reference(
            db,
            neighborhood_repository,
            id_neighborhood,
            field="id_neighborhood",
            label="Barrio",
        )

    @staticmethod
    def _admin_row(db: Session, id_client: int) -> ClientAdminRow:
        row = client_repository.get_admin_row(db, id_client)
        if row is None:
            raise EntityNotFoundError("Cliente", id_client)
        return ClientAdminRow.model_validate(row, from_attributes=True)


# Instancia única para inyectar en el router
client_service = ClientService()
