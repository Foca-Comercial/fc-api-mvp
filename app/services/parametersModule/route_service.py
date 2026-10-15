from sqlalchemy.orm import Session

from app.models.parametersModule.route import Route
from app.repositories.coreModule.client_repository import client_repository
from app.repositories.coreModule.client_route_repository import client_route_repository
from app.repositories.parametersModule.route_repository import route_repository
from app.schemas.parametersModule.route_schema import (
    RouteAvailableClientResponse,
    RouteCardResponse,
    RouteClientResponse,
    RouteCreate,
    RouteUpdate,
)
from app.services.base_service import BaseService, UniqueRule
from app.services.validation import ensure_reference
from app.utils.exceptions.business_exceptions import (
    BusinessValidationError,
    ConflictError,
    EntityNotFoundError,
)


class RouteService(BaseService[Route, RouteCreate, RouteUpdate]):
    unique_rules = (UniqueRule("name", "Nombre de ruta"),)

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=route_repository, entity_name="Ruta")

    # --- Vista de Rutas ---

    def get_cards(
        self, db: Session, *, only_active: bool = False
    ) -> list[RouteCardResponse]:
        return [
            RouteCardResponse(
                id_route=route.id_route,
                name=route.name,
                days_week=route.days_week,
                departure_time=route.departure_time,
                active=route.active,
                clients_count=clients_count,
            )
            for route, clients_count in route_repository.get_cards(
                db, only_active=only_active
            )
        ]

    def get_clients(self, db: Session, id_route: int) -> list[RouteClientResponse]:
        self.get(db, id_route)  # 404 si la ruta no existe
        return [
            RouteClientResponse.model_validate(row)
            for row in route_repository.get_clients(db, id_route)
        ]

    def get_available_clients(
        self, db: Session, id_route: int, *, name: str | None = None, limit: int = 20
    ) -> list[RouteAvailableClientResponse]:
        self.get(db, id_route)
        return [
            RouteAvailableClientResponse.model_validate(row)
            for row in route_repository.get_available_clients(
                db, id_route, name=name, limit=limit
            )
        ]

    def assign_client(
        self, db: Session, *, id_route: int, id_client: int
    ) -> RouteClientResponse:
        # La ruta puede estar inactiva: sus clientes se siguen gestionando.
        self.get(db, id_route)
        ensure_reference(
            db, client_repository, id_client, field="id_client", label="Cliente"
        )
        # Los clientes temporales (creados desde un pedido) no se asignan a rutas
        if not client_repository.get(db, id_client).is_registered:
            raise BusinessValidationError(
                "Solo se pueden asignar a una ruta clientes registrados.",
                field="id_client",
                code="CLIENT_NOT_REGISTERED",
            )
        if client_route_repository.get_by_pair(
            db, id_route=id_route, id_client=id_client
        ):
            raise ConflictError(
                "El cliente ya está asignado a esta ruta.",
                field="id_client",
                code="DUPLICATE_PAIR",
            )

        client_route_repository.add(
            db, obj_in_data={"id_route": id_route, "id_client": id_client}
        )
        db.commit()
        return next(
            c for c in self.get_clients(db, id_route) if c.id_client == id_client
        )

    def unassign_client(self, db: Session, *, id_route: int, id_client: int) -> None:
        self.get(db, id_route)
        link = client_route_repository.get_by_pair(
            db, id_route=id_route, id_client=id_client
        )
        if link is None:
            raise EntityNotFoundError("Cliente en la ruta", id_client)
        client_route_repository.delete(db, db_obj=link)
        db.commit()


# Instancia única para inyectar en el router
route_service = RouteService()
