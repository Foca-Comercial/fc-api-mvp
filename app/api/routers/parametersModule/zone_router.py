from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.parametersModule.zone_schema import (
    ZoneCreate,
    ZoneResponse,
    ZoneUpdate,
)
from app.services.parametersModule.zone_service import zone_service
from app.utils.enums.delete_type import DeletionType

router = APIRouter(prefix="/zones", tags=["Zones"])


@router.get("/", response_model=list[ZoneResponse])
def get_all_zones(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return zone_service.get_all(db, skip=skip, limit=limit)


@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(zone_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return zone_service.get(db, id=zone_id)


@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(zone_in: ZoneCreate, db: Session = Depends(get_db)):  # noqa: B008
    return zone_service.create(db, obj_in=zone_in)


@router.patch("/{zone_id}", response_model=ZoneResponse)
def update_zone(
    zone_id: int,
    zone_in: ZoneUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return zone_service.update(db, id=zone_id, obj_in=zone_in)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    zone_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return zone_service.remove(db, id=zone_id, strategy_type=strategy)
