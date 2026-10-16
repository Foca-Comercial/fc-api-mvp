from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.shift_closure_schema import ShiftClosureResponse
from app.services.coreModule.shift_closure_service import shift_closure_service

# Solo lectura (ADMIN): los cierres los genera la exportación del cierre de turno.
router = SecuredRouter(prefix="/shifts_closures", tags=["ShiftsClosures"])


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
