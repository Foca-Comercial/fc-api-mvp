from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.coreModule.client_schema import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
)
from app.services.coreModule.client_service import client_service

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("/", response_model=list[ClientResponse])
def get_all_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return client_service.get_all(db, skip=skip, limit=limit)


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


@router.delete("/{client_id}", response_model=ClientResponse)
def delete_client(client_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return client_service.remove(db, id=client_id)
