"""Escritura de una pestaña completa en Google Sheets.

El servicio de archivado depende de la interfaz `SheetsWriter`, no de gspread:
en los tests se inyecta un escritor falso y no se llama a Google.
"""

import json
from collections.abc import Sequence
from typing import Any, Protocol

from app.core.config import settings
from app.utils.exceptions.business_exceptions import ExternalServiceError

SERVICE = "Google Sheets"
CHUNK_ROWS = 5000  # filas por llamada a la API


class SheetsWriter(Protocol):
    def write_sheet(
        self,
        spreadsheet_id: str,
        title: str,
        header: Sequence[str],
        rows: Sequence[Sequence[Any]],
        money_columns: Sequence[int] = (),
    ) -> int:
        """Reemplaza el contenido de la pestaña `title` (la crea si no existe) y
        devuelve cuántas filas de datos quedaron escritas, leídas de vuelta."""
        ...


def _column_letter(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


class GoogleSheetsWriter:
    def __init__(self, credentials_file: str) -> None:
        import gspread  # import diferido: solo se necesita al exportar

        self._gspread = gspread
        try:
            self._client = gspread.service_account(filename=credentials_file)
            with open(credentials_file, encoding="utf-8") as file:
                self._email = json.load(file).get("client_email", "")
        except FileNotFoundError as error:
            raise ExternalServiceError(
                SERVICE, f"No se encontró el archivo de credenciales: {credentials_file}"
            ) from error
        except (ValueError, KeyError) as error:
            raise ExternalServiceError(
                SERVICE, "El archivo de credenciales no es una llave JSON válida."
            ) from error

    def write_sheet(self, spreadsheet_id, title, header, rows, money_columns=()) -> int:
        gspread = self._gspread
        try:
            spreadsheet = self._client.open_by_key(spreadsheet_id)
            total_rows = len(rows) + 1
            total_cols = len(header)
            try:
                worksheet = spreadsheet.worksheet(title)
                worksheet.clear()
                worksheet.resize(rows=total_rows, cols=total_cols)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=title, rows=total_rows, cols=total_cols
                )

            worksheet.update(values=[list(header)], range_name="A1")
            for start in range(0, len(rows), CHUNK_ROWS):
                chunk = [list(r) for r in rows[start : start + CHUNK_ROWS]]
                worksheet.update(values=chunk, range_name=f"A{start + 2}")

            self._format(worksheet, total_rows, total_cols, money_columns)

            # Verificación: se cuenta lo que realmente quedó en la hoja
            written = len(worksheet.col_values(1)) - 1
        except gspread.exceptions.SpreadsheetNotFound as error:
            raise ExternalServiceError(SERVICE, self._access_hint()) from error
        except PermissionError as error:
            raise ExternalServiceError(SERVICE, self._access_hint()) from error
        except gspread.exceptions.APIError as error:
            if getattr(error, "code", None) in (403, 404):
                raise ExternalServiceError(SERVICE, self._access_hint()) from error
            raise ExternalServiceError(SERVICE, str(error)) from error
        return written

    def _format(self, worksheet, total_rows, total_cols, money_columns) -> None:
        last_col = _column_letter(total_cols - 1)
        worksheet.freeze(rows=1)
        worksheet.format(
            f"A1:{last_col}1",
            {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 0.98},
            },
        )
        for column in money_columns:
            letter = _column_letter(column)
            worksheet.format(
                f"{letter}2:{letter}{total_rows}",
                {"numberFormat": {"type": "CURRENCY", "pattern": "$#,##0"}},
            )
        worksheet.set_basic_filter(f"A1:{last_col}{total_rows}")

    def _access_hint(self) -> str:
        email = self._email or "el correo de la cuenta de servicio"
        return (
            "No se pudo abrir el spreadsheet. Verifica el ID registrado y que esté "
            f"compartido como Editor con {email}."
        )


def get_sheets_writer() -> SheetsWriter:
    """Dependencia de FastAPI. En los tests se reemplaza por un escritor falso."""
    if settings.GOOGLE_CREDENTIALS_FILE is None:
        raise ExternalServiceError(
            SERVICE, "Falta configurar GOOGLE_CREDENTIALS_FILE en el .env."
        )
    return GoogleSheetsWriter(str(settings.GOOGLE_CREDENTIALS_FILE))
