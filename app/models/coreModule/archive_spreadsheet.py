from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ArchiveSpreadsheet(Base):
    """Spreadsheet de Google Sheets donde se exportan los pedidos de cada año.

    Lo crea el usuario en su Drive y lo comparte (editor) con la cuenta de
    servicio; el sistema agrega una pestaña por mes.
    """

    __tablename__ = "archive_spreadsheet"
    __table_args__ = (
        CheckConstraint("year BETWEEN 2020 AND 2100", name="chk_archive_spreadsheet_year"),
    )

    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    spreadsheet_id: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
