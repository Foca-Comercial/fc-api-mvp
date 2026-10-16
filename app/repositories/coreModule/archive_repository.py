from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.coreModule.archive_spreadsheet import ArchiveSpreadsheet
from app.models.coreModule.monthly_archive import MonthlyArchive


class RepositoryArchiveSpreadsheet:
    def get(self, db: Session, year: int) -> ArchiveSpreadsheet | None:
        return db.get(ArchiveSpreadsheet, year)

    def get_all(self, db: Session) -> list[ArchiveSpreadsheet]:
        stmt = select(ArchiveSpreadsheet).order_by(ArchiveSpreadsheet.year.desc())
        return list(db.scalars(stmt).all())

    def upsert(self, db: Session, *, year: int, spreadsheet_id: str) -> ArchiveSpreadsheet:
        row = self.get(db, year)
        if row is None:
            row = ArchiveSpreadsheet(year=year, spreadsheet_id=spreadsheet_id)
            db.add(row)
        else:
            row.spreadsheet_id = spreadsheet_id
        db.flush()
        return row


class RepositoryMonthlyArchive:
    def get(self, db: Session, archive_month) -> MonthlyArchive | None:
        return db.get(MonthlyArchive, archive_month)

    def get_all(self, db: Session) -> list[MonthlyArchive]:
        stmt = select(MonthlyArchive).order_by(MonthlyArchive.archive_month.desc())
        return list(db.scalars(stmt).all())

    def save_export(
        self, db: Session, *, archive_month: date, **values
    ) -> MonthlyArchive:
        """Crea o actualiza la fila del mes con los datos de la última exportación."""
        row = self.get(db, archive_month)
        if row is None:
            row = MonthlyArchive(archive_month=archive_month, **values)
            db.add(row)
        else:
            for field, value in values.items():
                setattr(row, field, value)
        db.flush()
        return row


# Clave fija del bloqueo de archivado: dos exportaciones/purgas no corren a la vez
ARCHIVE_LOCK_KEY = 7_401_202_601


def lock_archive(db: Session) -> None:
    """Bloqueo exclusivo hasta el fin de la transacción (pg_advisory_xact_lock)."""
    db.execute(select(func.pg_advisory_xact_lock(ARCHIVE_LOCK_KEY)))


archive_spreadsheet_repository = RepositoryArchiveSpreadsheet()
monthly_archive_repository = RepositoryMonthlyArchive()
