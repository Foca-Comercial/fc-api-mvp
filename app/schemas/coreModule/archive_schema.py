import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.enums.archive_status import ArchiveStatus

# ID de Google: letras, números, "-" y "_". Se acepta también la URL completa
# (https://docs.google.com/spreadsheets/d/<ID>/edit...) y se extrae el ID.
_SPREADSHEET_URL = re.compile(r"/spreadsheets/d/([A-Za-z0-9_-]+)")
_SPREADSHEET_ID = re.compile(r"^[A-Za-z0-9_-]{20,100}$")


class ArchiveSpreadsheetSet(BaseModel):
    spreadsheet: str = Field(
        ..., description="ID del spreadsheet o su URL completa de Google Sheets"
    )

    @field_validator("spreadsheet")
    @classmethod
    def _extract_id(cls, value: str) -> str:
        value = value.strip()
        match = _SPREADSHEET_URL.search(value)
        spreadsheet_id = match.group(1) if match else value
        if not _SPREADSHEET_ID.match(spreadsheet_id):
            raise ValueError("No es un ID ni una URL válida de Google Sheets.")
        return spreadsheet_id


class ArchiveSpreadsheetResponse(BaseModel):
    year: int
    spreadsheet_id: str
    url: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonthlyArchiveResponse(BaseModel):
    month: str = Field(..., description="AAAA-MM")
    status: ArchiveStatus
    spreadsheet_id: str
    sheet_title: str
    orders_count: int
    rows_count: int
    total_sales: Decimal
    exported_at: datetime
    id_user_exported: int | None
    purged_at: datetime | None
    id_user_purged: int | None


def month_label(month: date) -> str:
    return f"{month.year:04d}-{month.month:02d}"


def spreadsheet_url(spreadsheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
