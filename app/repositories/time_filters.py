"""Filtros por fecha local (Bogotá) sobre columnas TIMESTAMPTZ.

Todos comparan la columna con un RANGO de instantes (`col >= inicio AND col < fin`)
para que PostgreSQL use el índice de la columna. Nunca aplicar funciones sobre la
columna (`date(timezone(..., col))`) en un WHERE: eso recorre la tabla completa.
"""

from datetime import date

from sqlalchemy import ColumnElement, and_, func, text

from app.core.timezone import BOGOTA_TZ, bogota_date_range, bogota_day_range


def on_bogota_day(column, day: date) -> ColumnElement[bool]:
    start, end = bogota_day_range(day)
    return and_(column >= start, column < end)


def between_bogota_dates(column, date_from: date, date_to: date) -> ColumnElement[bool]:
    start, end = bogota_date_range(date_from, date_to)
    return and_(column >= start, column < end)


def on_db_today(column) -> ColumnElement[bool]:
    """Día de HOY según la BD (now() = inicio de la transacción), en Bogotá.

    Se usa donde debe coincidir exactamente con el día que recibe
    creation_datetime (server_default now()), p. ej. junto al consecutivo.
    """
    local_midnight = func.date_trunc("day", func.timezone(BOGOTA_TZ.key, func.now()))
    start = func.timezone(BOGOTA_TZ.key, local_midnight)  # medianoche local -> instante
    return and_(column >= start, column < start + text("interval '1 day'"))
