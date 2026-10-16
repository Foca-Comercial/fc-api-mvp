import re
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.timezone import today_bogota

from app.models.coreModule.archive_spreadsheet import ArchiveSpreadsheet
from app.models.coreModule.monthly_archive import MonthlyArchive
from app.repositories.coreModule.archive_repository import (
    archive_spreadsheet_repository,
    lock_archive,
    monthly_archive_repository,
)
from app.repositories.coreModule.order_repository import order_repository
from app.schemas.coreModule.archive_schema import (
    ArchiveSpreadsheetResponse,
    MonthlyArchiveResponse,
    month_label,
    spreadsheet_url,
)
from app.services.coreModule.archive_export import MONEY_COLUMNS, build_export_table
from app.services.coreModule.sheets_writer import SERVICE, SheetsWriter
from app.utils.enums.archive_status import ArchiveStatus
from app.utils.exceptions.business_exceptions import (
    BusinessValidationError,
    ConflictError,
    ExternalServiceError,
)

_PERIOD = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def parse_period(period: str) -> date:
    """"2026-09" -> date(2026, 9, 1)."""
    match = _PERIOD.match(period)
    if not match:
        raise BusinessValidationError(
            "El mes debe tener el formato AAAA-MM.", field="period", code="INVALID_PERIOD"
        )
    return date(int(match.group(1)), int(match.group(2)), 1)


class ArchiveService:
    """Archivado mensual de pedidos: configuración, bitácora y exportación.

    La purga (borrado de la BD) se agrega en H5.
    """

    # --- Exportación ---

    def export_month(
        self, db: Session, *, period: str, id_user: int, writer: SheetsWriter
    ) -> MonthlyArchiveResponse:
        """Escribe (o reescribe) la pestaña del mes en Sheets y lo registra en la
        bitácora como EXPORTED. Los pedidos NO se borran."""
        archive_month = parse_period(period)
        if archive_month > today_bogota().replace(day=1):
            raise BusinessValidationError(
                "No se puede exportar un mes futuro.",
                field="period",
                code="MONTH_IN_FUTURE",
            )

        lock_archive(db)  # una exportación/purga a la vez
        row = self._export(db, archive_month=archive_month, writer=writer)
        row.id_user_exported = id_user
        db.commit()
        db.refresh(row)
        return self._archive_response(row)

    def _export(self, db: Session, *, archive_month: date, writer: SheetsWriter):
        """Exporta y verifica, sin commit. Reutilizable por la purga (H5)."""
        existing = monthly_archive_repository.get(db, archive_month)
        if existing is not None and existing.status == ArchiveStatus.PURGED:
            raise ConflictError(
                f"El mes {month_label(archive_month)} ya fue purgado; sus pedidos ya no "
                "están en la base de datos.",
                field="period",
                code="MONTH_ALREADY_PURGED",
            )

        sheet = archive_spreadsheet_repository.get(db, archive_month.year)
        if sheet is None:
            raise BusinessValidationError(
                f"No hay spreadsheet registrado para {archive_month.year}. Regístralo "
                f"con PUT /archive/spreadsheets/{archive_month.year}.",
                field="period",
                code="SPREADSHEET_NOT_CONFIGURED",
            )

        source = order_repository.get_month_export_rows(
            db, archive_month.year, archive_month.month
        )
        if not source:
            raise BusinessValidationError(
                f"No hay pedidos de {month_label(archive_month)} para exportar.",
                field="period",
                code="NO_ORDERS_TO_EXPORT",
            )

        table = build_export_table(source)
        title = month_label(archive_month)
        written = writer.write_sheet(
            sheet.spreadsheet_id, title, table.header, table.rows, MONEY_COLUMNS
        )
        if written != len(table.rows):
            raise ExternalServiceError(
                SERVICE,
                f"La verificación falló: se esperaban {len(table.rows)} filas en la "
                f"pestaña {title} y hay {written}. Reintenta la exportación.",
            )

        return monthly_archive_repository.save_export(
            db,
            archive_month=archive_month,
            status=ArchiveStatus.EXPORTED,
            spreadsheet_id=sheet.spreadsheet_id,
            sheet_title=title,
            orders_count=table.orders_count,
            rows_count=len(table.rows),
            total_sales=table.total_sales,
            exported_at=datetime.now(timezone.utc),
        )

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
