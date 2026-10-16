from datetime import date

from fastapi import Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.core.timezone import today_bogota
from app.db.database import get_db
from app.schemas.coreModule.shift_closure_schema import (
    ShiftClosureResponse,
    ShiftClosureSummary,
)
from app.services.coreModule.closure_export import MEDIA_TYPE
from app.services.coreModule.shift_closure_service import shift_closure_service

# CRUD de solo lectura (ADMIN): los cierres los genera la exportación del cierre.
router = SecuredRouter(prefix="/shifts_closures", tags=["ShiftsClosures"])


# -----------------------------------------------------
# Vista Cierre (literal: antes de /{shift_closure_id})
# -----------------------------------------------------
@router.get(
    "/summary",
    response_model=ShiftClosureSummary,
    roles=["GESTOR_COMERCIAL"],
)
def get_closure_summary(
    target_date: date | None = Query(default_factory=today_bogota),  # type: ignore  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return shift_closure_service.get_summary(db, target_date)  # type: ignore


# Exporta (o reexporta) el cierre del día a Excel para Siigo, p. ej.
# POST /shifts_closures/2026-10-16/export. Marca los cierres como exportados.
@router.post(
    "/{closure_date}/export",
    response_class=Response,
    responses={
        200: {
            "content": {MEDIA_TYPE: {}},
            "description": "Excel (.xlsx) con las facturas globales por vendedor.",
        }
    },
    roles=["GESTOR_COMERCIAL"],
)
def export_closure(
    closure_date: date = Path(..., examples=["2026-10-16"]),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    filename, content = shift_closure_service.export_day(db, closure_date)
    return Response(
        content=content,
        media_type=MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
