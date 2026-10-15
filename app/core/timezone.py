from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

BOGOTA_TZ = ZoneInfo("America/Bogota")


def today_bogota() -> date:
    """Fecha actual en Bogotá, independiente de la zona del servidor."""
    return datetime.now(BOGOTA_TZ).date()


def bogota_day_range(day: date) -> tuple[datetime, datetime]:
    """[inicio, fin) del día `day` en Bogotá, como instantes con zona horaria.

    Sirve para filtrar columnas TIMESTAMPTZ por rango
    (`col >= inicio AND col < fin`), que sí aprovecha el índice, en lugar de
    `date(timezone(..., col)) = día`, que obliga a recorrer toda la tabla.
    """
    start = datetime.combine(day, time.min, tzinfo=BOGOTA_TZ)
    return start, start + timedelta(days=1)


def bogota_month_range(year: int, month: int) -> tuple[datetime, datetime]:
    """[inicio, fin) del mes `year`-`month` en Bogotá."""
    start = datetime(year, month, 1, tzinfo=BOGOTA_TZ)
    next_month = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=BOGOTA_TZ)
    return start, next_month


def bogota_date_range(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    """[inicio de date_from, fin de date_to) en Bogotá (ambos días incluidos)."""
    return bogota_day_range(date_from)[0], bogota_day_range(date_to)[1]
