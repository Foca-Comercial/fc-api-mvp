from sqlalchemy import select
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


archive_spreadsheet_repository = RepositoryArchiveSpreadsheet()
monthly_archive_repository = RepositoryMonthlyArchive()
