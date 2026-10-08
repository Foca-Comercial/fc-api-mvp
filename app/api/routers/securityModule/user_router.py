from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.securityModule.user_schema import (
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.securityModule.user_service import user_service

router = SecuredRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserResponse])
def get_all_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return user_service.get_all(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return user_service.get(db, id=user_id)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):  # noqa: B008
    return user_service.create(db, obj_in=user_in)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return user_service.update(db, id=user_id, obj_in=user_in)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):  # noqa: B008
    user_service.remove(db, id=user_id)
