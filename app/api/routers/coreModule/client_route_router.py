from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.coreModule.client_route_schema import (
    ClientRouteCreate,
    ClientRouteResponse,
    ClientRouteUpdate,
)
from app.services.coreModule.client_route_service import client_route_service

router = APIRouter(prefix="/clients_routes", tags=["ClientsRoutes"])


@router.get("/", response_model=list[ClientRouteResponse])
def get_all_clients_routes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),  # noqa: B008
):
    return client_route_service.get_all(db, skip=skip, limit=limit)


@router.get("/{client_route_id}", response_model=ClientRouteResponse)
def get_client(client_route_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return client_route_service.get(db, id=client_route_id)


@router.post(
    "/", response_model=ClientRouteResponse, status_code=status.HTTP_201_CREATED
)
def create_client(client_route_in: ClientRouteCreate, db: Session = Depends(get_db)):  # noqa: B008
    return client_route_service.create(db, obj_in=client_route_in)


@router.patch("/{client_route_id}", response_model=ClientRouteResponse)
def update_client(
    client_route_id: int,
    client_route_in: ClientRouteUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return client_route_service.update(db, id=client_route_id, obj_in=client_route_in)


@router.delete("/{client_route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_route_id: int, db: Session = Depends(get_db)):  # noqa: B008
    client_route_service.remove(db, id=client_route_id)
