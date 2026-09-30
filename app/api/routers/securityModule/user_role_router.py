from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.securityModule.user_role_schema import (
    UserRoleCreate,
    UserRoleResponse,
    UserRoleUpdate,
)
from app.services.securityModule.user_role_service import user_role_service

router = APIRouter(prefix="/users_roles", tags=["UsersRoles"])


@router.get("/", response_model=list[UserRoleResponse])
def get_all_users_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return user_role_service.get_all(db, skip=skip, limit=limit)


@router.get("/{user_role_id}", response_model=UserRoleResponse)
def get_user(user_role_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return user_role_service.get(db, id=user_role_id)


@router.post("/", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_role_in: UserRoleCreate, db: Session = Depends(get_db)):  # noqa: B008
    return user_role_service.create(db, obj_in=user_role_in)


@router.patch("/{user_role_id}", response_model=UserRoleResponse)
def update_user(
    user_role_id: int,
    user_role_in: UserRoleUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return user_role_service.update(db, id=user_role_id, obj_in=user_role_in)


@router.delete("/{user_role_id}", response_model=UserRoleResponse)
def delete_user(user_role_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return user_role_service.remove(db, id=user_role_id)
