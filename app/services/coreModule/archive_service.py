from sqlalchemy.orm import Session

from app.models.coreModule.archive_spreadsheet import ArchiveSpreadsheet
from app.models.coreModule.monthly_archive import MonthlyArchive
from app.repositories.coreModule.archive_repository import (
    archive_spreadsheet_repository,
    monthly_archive_repository,
)
from app.schemas.coreModule.archive_schema import (
    ArchiveSpreadsheetResponse,
    MonthlyArchiveResponse,
    month_label,
    spreadsheet_url,
)


class ArchiveService:
    """Archivado mensual de pedidos: configuración y bitácora (H3).

    La exportación a Google Sheets y la purga se agregan en H4/H5.
    """

    # --- Spreadsheet por año ---

    def list_spreadsheets(self, db: Session) -> list[ArchiveSpreadsheetResponse]:
        return [
            self._spreadsheet_response(row)
            for row in archive_spreadsheet_repository.get_all(db)
        ]

    def set_spreadsheet(
        self, db: Session, *, year: int, spreadsheet_id: str
    ) -> ArchiveSpreadsheetResponse:
        row = archive_spreadsheet_repository.upsert(
            db, year=year, spreadsheet_id=spreadsheet_id
        )
        db.commit()
        db.refresh(row)
        return self._spreadsheet_response(row)

    # --- Bitácora ---

    def list_archives(self, db: Session) -> list[MonthlyArchiveResponse]:
        return [
            self._archive_response(row) for row in monthly_archive_repository.get_all(db)
        ]

    # --- Mapeo ---

    @staticmethod
    def _spreadsheet_response(row: ArchiveSpreadsheet) -> ArchiveSpreadsheetResponse:
        return ArchiveSpreadsheetResponse(
            year=row.year,
            spreadsheet_id=row.spreadsheet_id,
            url=spreadsheet_url(row.spreadsheet_id),
            updated_at=row.updated_at,
        )

    @staticmethod
    def _archive_response(row: MonthlyArchive) -> MonthlyArchiveResponse:
        return MonthlyArchiveResponse(
            month=month_label(row.archive_month),
            status=row.status,
            spreadsheet_id=row.spreadsheet_id,
            sheet_title=row.sheet_title,
            orders_count=row.orders_count,
            rows_count=row.rows_count,
            total_sales=row.total_sales,
            exported_at=row.exported_at,
            id_user_exported=row.id_user_exported,
            purged_at=row.purged_at,
            id_user_purged=row.id_user_purged,
        )


archive_service = ArchiveService()
