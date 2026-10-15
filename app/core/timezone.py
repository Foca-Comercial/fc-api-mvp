from datetime import date, datetime
from zoneinfo import ZoneInfo

BOGOTA_TZ = ZoneInfo("America/Bogota")


def today_bogota() -> date:
    """Fecha actual en Bogotá, independiente de la zona del servidor."""
    return datetime.now(BOGOTA_TZ).date()
