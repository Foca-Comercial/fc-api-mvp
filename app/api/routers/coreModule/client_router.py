from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.client_schema import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
)
from app.services.coreModule.client_service import client_service
from app.utils.enums.delete_type import DeletionType

router = SecuredRouter(prefix="/clients", tags=["Clients"])


@router.get("/", response_model=list[ClientResponse])
def get_all_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return client_service.get_all(db, skip=skip, limit=limit)


@router.get("/search", response_model=list[ClientResponse], roles=["GESTOR_COMERCIAL"])
def search_clients(name: str = Query(..., min_length=2), db: Session = Depends(get_db)):  # noqa: B008
    return client_service.search_by_name(db, name=name)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return client_service.get(db, id=client_id)


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(client_in: ClientCreate, db: Session = Depends(get_db)):  # noqa: B008
    return client_service.create(db, obj_in=client_in)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return client_service.update(db, id=client_id, obj_in=client_in)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return client_service.remove(db, id=client_id, strategy_type=strategy)
