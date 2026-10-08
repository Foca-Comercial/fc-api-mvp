from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.parametersModule.neighborhood_schema import (
    NeighborhoodCreate,
    NeighborhoodResponse,
    NeighborhoodUpdate,
)
from app.services.parametersModule.neighborhood_service import neighborhood_service
from app.utils.enums.delete_type import DeletionType

router = SecuredRouter(prefix="/neighborhoods", tags=["Neighborhoods"])


@router.get("/", response_model=list[NeighborhoodResponse])
def get_all_neighborhoods(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),  # noqa: B008
):
    return neighborhood_service.get_all(db, skip=skip, limit=limit)


@router.get("/{neighborhood_id}", response_model=NeighborhoodResponse)
def get_neighborhood(neighborhood_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return neighborhood_service.get(db, id=neighborhood_id)


@router.post(
    "/", response_model=NeighborhoodResponse, status_code=status.HTTP_201_CREATED
)
def create_neighborhood(
    neighborhood_in: NeighborhoodCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return neighborhood_service.create(db, obj_in=neighborhood_in)


@router.patch("/{neighborhood_id}", response_model=NeighborhoodResponse)
def update_neighborhood(
    neighborhood_id: int,
    neighborhood_in: NeighborhoodUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return neighborhood_service.update(db, id=neighborhood_id, obj_in=neighborhood_in)


@router.delete("/{neighborhood_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_neighborhood(
    neighborhood_id: int,
    strategy: DeletionType = Query(DeletionType.SOFT),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return neighborhood_service.remove(db, id=neighborhood_id, strategy_type=strategy)
