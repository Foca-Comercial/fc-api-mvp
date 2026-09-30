from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.coreModule.shift_closure_schema import (
    ShiftClosureCreate,
    ShiftClosureResponse,
    ShiftClosureUpdate,
)
from app.services.coreModule.shift_closure_service import shift_closure_service

router = APIRouter(prefix="/shifts_closures", tags=["ShiftsClosures"])


@router.get("/", response_model=list[ShiftClosureResponse])
def get_all_shifts_closures(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),  # noqa: B008
):
    return shift_closure_service.get_all(db, skip=skip, limit=limit)


@router.get("/{shift_closure_id}", response_model=ShiftClosureResponse)
def get_shift(shift_closure_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return shift_closure_service.get(db, id=shift_closure_id)


@router.post(
    "/", response_model=ShiftClosureResponse, status_code=status.HTTP_201_CREATED
)
def create_shift(shift_closure_in: ShiftClosureCreate, db: Session = Depends(get_db)):  # noqa: B008
    return shift_closure_service.create(db, obj_in=shift_closure_in)


@router.patch("/{shift_closure_id}", response_model=ShiftClosureResponse)
def update_shift(
    shift_closure_id: int,
    shift_closure_in: ShiftClosureUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return shift_closure_service.update(
        db, id=shift_closure_id, obj_in=shift_closure_in
    )


@router.delete("/{shift_closure_id}", response_model=ShiftClosureResponse)
def delete_shift(shift_closure_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return shift_closure_service.remove(db, id=shift_closure_id)
