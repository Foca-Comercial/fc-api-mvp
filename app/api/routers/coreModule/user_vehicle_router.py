from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.coreModule.user_vehicle_schema import (
    UserVehicleCreate,
    UserVehicleResponse,
    UserVehicleUpdate,
)
from app.services.coreModule.user_vehicle_service import user_vehicle_service

router = APIRouter(prefix="/users_vehicles", tags=["UsersVehicles"])


@router.get("/", response_model=list[UserVehicleResponse])
def get_all_users_vehicles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),  # noqa: B008
):
    return user_vehicle_service.get_all(db, skip=skip, limit=limit)


@router.get("/{user_vehicle_id}", response_model=UserVehicleResponse)
def get_user(user_vehicle_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return user_vehicle_service.get(db, id=user_vehicle_id)


@router.post(
    "/", response_model=UserVehicleResponse, status_code=status.HTTP_201_CREATED
)
def create_user(user_vehicle_in: UserVehicleCreate, db: Session = Depends(get_db)):  # noqa: B008
    return user_vehicle_service.create(db, obj_in=user_vehicle_in)


@router.patch("/{user_vehicle_id}", response_model=UserVehicleResponse)
def update_user(
    user_vehicle_id: int,
    user_vehicle_in: UserVehicleUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return user_vehicle_service.update(db, id=user_vehicle_id, obj_in=user_vehicle_in)


@router.delete("/{user_vehicle_id}", response_model=UserVehicleResponse)
def delete_user(user_vehicle_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return user_vehicle_service.remove(db, id=user_vehicle_id)
