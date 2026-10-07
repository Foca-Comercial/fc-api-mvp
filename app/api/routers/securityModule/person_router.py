from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.securityModule.person_schema import (
    PersonCreate,
    PersonResponse,
    PersonUpdate,
)
from app.services.securityModule.person_service import person_service
from app.utils.enums.delete_type import DeletionType

router = APIRouter(prefix="/persons", tags=["Persons"])


@router.get("/", response_model=list[PersonResponse])
def get_all_persons(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return person_service.get_all(db, skip=skip, limit=limit)


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return person_service.get(db, id=person_id)


@router.post("/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_person(person_in: PersonCreate, db: Session = Depends(get_db)):  # noqa: B008
    return person_service.create(db, obj_in=person_in)


@router.patch("/{person_id}", response_model=PersonResponse)
def update_person(
    person_id: int,
    person_in: PersonUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return person_service.update(db, id=person_id, obj_in=person_in)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return person_service.remove(db, id=person_id, strategy_type=strategy)
