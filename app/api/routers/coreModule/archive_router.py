from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.archive_schema import (
    ArchiveSpreadsheetResponse,
    ArchiveSpreadsheetSet,
    MonthlyArchiveResponse,
)
from app.services.coreModule.archive_service import archive_service

# Archivado mensual: solo ADMINISTRADOR (rol por defecto de SecuredRouter)
router = SecuredRouter(prefix="/archive", tags=["Archive"])


@router.get("/", response_model=list[MonthlyArchiveResponse])
def list_archives(db: Session = Depends(get_db)):  # noqa: B008
    return archive_service.list_archives(db)


@router.get("/spreadsheets", response_model=list[ArchiveSpreadsheetResponse])
def list_spreadsheets(db: Session = Depends(get_db)):  # noqa: B008
    return archive_service.list_spreadsheets(db)


@router.put("/spreadsheets/{year}", response_model=ArchiveSpreadsheetResponse)
def set_spreadsheet(
    body: ArchiveSpreadsheetSet,
    year: int = Path(..., ge=2020, le=2100),
    db: Session = Depends(get_db),  # noqa: B008
):
    return archive_service.set_spreadsheet(
        db, year=year, spreadsheet_id=body.spreadsheet
    )
