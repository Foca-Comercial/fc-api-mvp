from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.parametersModule.route_schema import (
    RouteAvailableClientResponse,
    RouteCardResponse,
    RouteClientAssign,
    RouteClientResponse,
    RouteCreate,
    RouteResponse,
    RouteUpdate,
)
from app.services.parametersModule.route_service import route_service
from app.utils.enums.delete_type import DeletionType

router = SecuredRouter(prefix="/routes", tags=["Routes"])

# Vista de Rutas: GESTOR_COMERCIAL (y ADMINISTRADOR, que siempre pasa)
ROUTE_MANAGERS = ["GESTOR_COMERCIAL"]


@router.get("/", response_model=list[RouteResponse], roles=ROUTE_MANAGERS)
def get_all_routes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return route_service.get_all(db, skip=skip, limit=limit)


# Literal antes de /{route_id}
@router.get("/cards", response_model=list[RouteCardResponse], roles=ROUTE_MANAGERS)
def get_route_cards(
    only_active: bool = False,
    db: Session = Depends(get_db),  # noqa: B008
):
    return route_service.get_cards(db, only_active=only_active)


@router.get("/{route_id}", response_model=RouteResponse, roles=ROUTE_MANAGERS)
def get_route(route_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return route_service.get(db, id=route_id)


@router.post(
    "/",
    response_model=RouteResponse,
    status_code=status.HTTP_201_CREATED,
    roles=ROUTE_MANAGERS,
)
def create_route(route_in: RouteCreate, db: Session = Depends(get_db)):  # noqa: B008
    return route_service.create(db, obj_in=route_in)


@router.patch("/{route_id}", response_model=RouteResponse, roles=ROUTE_MANAGERS)
def update_route(
    route_id: int,
    route_in: RouteUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return route_service.update(db, id=route_id, obj_in=route_in)


# Solo ADMINISTRADOR: desactivar/borrar una ruta
@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return route_service.remove(db, id=route_id, strategy_type=strategy)


# --- Clientes de una ruta ---


@router.get(
    "/{route_id}/clients",
    response_model=list[RouteClientResponse],
    roles=ROUTE_MANAGERS,
)
def get_route_clients(route_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return route_service.get_clients(db, route_id)


# Selector para asignar: solo clientes registrados, activos y sin asignar
@router.get(
    "/{route_id}/available-clients",
    response_model=list[RouteAvailableClientResponse],
    roles=ROUTE_MANAGERS,
)
def get_route_available_clients(
    route_id: int,
    name: str | None = Query(None, min_length=2),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),  # noqa: B008
):
    return route_service.get_available_clients(db, route_id, name=name, limit=limit)


@router.post(
    "/{route_id}/clients",
    response_model=RouteClientResponse,
    status_code=status.HTTP_201_CREATED,
    roles=ROUTE_MANAGERS,
)
def assign_client_to_route(
    route_id: int,
    body: RouteClientAssign,
    db: Session = Depends(get_db),  # noqa: B008
):
    return route_service.assign_client(db, id_route=route_id, id_client=body.id_client)


@router.delete(
    "/{route_id}/clients/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    roles=ROUTE_MANAGERS,
)
def unassign_client_from_route(
    route_id: int,
    client_id: int,
    db: Session = Depends(get_db),  # noqa: B008
):
    route_service.unassign_client(db, id_route=route_id, id_client=client_id)
