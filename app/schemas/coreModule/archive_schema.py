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


class PurgeResponse(BaseModel):
    archive: MonthlyArchiveResponse
    deleted_orders: int
    deleted_order_lines: int
    deleted_temporary_clients: int
    deleted_order_counters: int
    deleted_expired_sessions: int


class ArchiveMonthRow(BaseModel):
    """Un mes en la vista Archivo mensual: lo que hay en la BD y su archivado."""

    month: str = Field(..., description="AAAA-MM")
    orders_count: int = Field(..., description="Pedidos del mes en la BD")
    total_sales: Decimal = Field(
        ..., description="Suma de los pedidos del mes en la BD, sin cancelados"
    )
    status: ArchiveStatus | None = Field(
        None, description="null = nunca se ha exportado"
    )
    exported_at: datetime | None = None
    purged_at: datetime | None = None
    exported_orders: int | None = Field(
        None, description="Pedidos en la última exportación (o los purgados)"
    )
    spreadsheet_url: str | None = Field(
        None, description="Spreadsheet del año del mes (null = no registrado)"
    )
    retained: bool = Field(
        ..., description="Dentro de la retención: se exporta, pero no se purga"
    )
    unclosed_days: list[date] = Field(
        default_factory=list,
        description="Días con pedidos facturables sin cierre exportado (o con cambios "
        "posteriores). Solo se calcula para meses fuera de la retención: impiden "
        "purgarlos",
    )
    can_export: bool
    can_purge: bool


class ArchiveOverview(BaseModel):
    current_month: str = Field(..., description="AAAA-MM (Bogotá)")
    first_retained_month: str = Field(
        ..., description="Mes más antiguo que se conserva: los anteriores se purgan"
    )
    retention_months: int
    months: list[ArchiveMonthRow] = Field(
        ..., description="Del más reciente al más antiguo, hasta el mes vigente"
    )


def month_label(month: date) -> str:
    return f"{month.year:04d}-{month.month:02d}"


def spreadsheet_url(spreadsheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
