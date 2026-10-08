from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.parametersModule.vehicle_schema import (
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
)
from app.services.parametersModule.vehicle_service import vehicle_service
from app.utils.enums.delete_type import DeletionType

router = SecuredRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("/", response_model=list[VehicleResponse])
def get_all_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return vehicle_service.get_all(db, skip=skip, limit=limit)


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return vehicle_service.get(db, id=vehicle_id)


@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(vehicle_in: VehicleCreate, db: Session = Depends(get_db)):  # noqa: B008
    return vehicle_service.create(db, obj_in=vehicle_in)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: int,
    vehicle_in: VehicleUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return vehicle_service.update(db, id=vehicle_id, obj_in=vehicle_in)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    vehicle_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return vehicle_service.remove(db, id=vehicle_id, strategy_type=strategy)
