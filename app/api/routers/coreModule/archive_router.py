from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.archive_schema import (
    ArchiveSpreadsheetResponse,
    ArchiveSpreadsheetSet,
    MonthlyArchiveResponse,
)
from app.services.coreModule.archive_service import archive_service
from app.services.coreModule.sheets_writer import SheetsWriter, get_sheets_writer

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


# Exporta (o reexporta) un mes a Google Sheets, p. ej. POST /archive/2026-09/export
@router.post("/{period}/export", response_model=MonthlyArchiveResponse)
def export_month(
    period: str = Path(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-09"]),
    db: Session = Depends(get_db),  # noqa: B008
    current: CurrentUser = Depends(get_current_user),  # noqa: B008
    writer: SheetsWriter = Depends(get_sheets_writer),  # noqa: B008
):
    return archive_service.export_month(
        db, period=period, id_user=current.user.id_user, writer=writer
    )
