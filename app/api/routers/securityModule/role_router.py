from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.securityModule.role_schema import (
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from app.services.securityModule.role_service import role_service
from app.utils.enums.delete_type import DeletionType

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RoleResponse])
def get_all_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return role_service.get_all(db, skip=skip, limit=limit)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return role_service.get(db, id=role_id)


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(role_in: RoleCreate, db: Session = Depends(get_db)):  # noqa: B008
    return role_service.create(db, obj_in=role_in)


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return role_service.update(db, id=role_id, obj_in=role_in)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return role_service.remove(db, id=role_id, strategy_type=strategy)
