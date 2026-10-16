"""Archivado mensual (H4): exportación de un mes a Google Sheets.

Usa un escritor falso en memoria: no se conecta a Google.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.timezone import today_bogota
from app.models.coreModule.archive_spreadsheet import ArchiveSpreadsheet
from app.models.coreModule.monthly_archive import MonthlyArchive
from app.models.coreModule.order import Order
from app.services.coreModule.archive_export import HEADER, MONEY_COLUMNS
from app.utils.enums.archive_status import ArchiveStatus
from app.utils.enums.order_state import OrderState
from app.utils.exceptions.business_exceptions import ExternalServiceError
from tests.helpers import API, item

SHEET_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-abc"


@pytest.fixture()
def period(db) -> str:
    """Mes vigente, con su spreadsheet del año registrado."""
    today = today_bogota()
    db.add(ArchiveSpreadsheet(year=today.year, spreadsheet_id=SHEET_ID))
    db.commit()
    return f"{today:%Y-%m}"


def _export(client, period):
    return client.post(f"{API}/archive/{period}/export")


def test_exporta_una_fila_por_producto_y_registra_la_bitacora(
    admin, writer, create_order, period, data, db
):
    p0, p1, _ = data.products
    first = create_order(
        items=[item(p0, 2), item(p1, 1)],
        id_user_vehicle=data.user_vehicle.id_user_vehicle,
    )
    cancelled = create_order(items=[item(p0, 1)])
    db.get(Order, cancelled["id_order"]).state = OrderState.CANCELLED
    db.commit()

    response = _export(admin, period)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["month"] == period
    assert body["status"] == "EXPORTED"
    assert (body["orders_count"], body["rows_count"]) == (2, 3)
    assert Decimal(body["total_sales"]) == Decimal(first["order_total"])  # sin cancelado
    assert body["id_user_exported"] == data.taker.id_user

    sheet = writer.sheets[(SHEET_ID, period)]
    assert sheet["header"] == list(HEADER)
    assert sheet["money_columns"] == list(MONEY_COLUMNS)
    rows = sheet["rows"]
    assert len(rows) == 3
    by_code = {r[13]: r for r in rows if r[2] == first["purchase_order"]}
    row = by_code["Z91"]
    assert row[0] == today_bogota().isoformat()
    assert row[3] == "CLIENTE REGISTRADO"
    assert row[6] == "ZONA TEST"
    assert row[8] == "Z9 - Carlos Conductor"
    assert row[9] == "Ana Gestora"
    assert row[10] == "Pendiente"
    assert (row[15], row[16], row[17]) == (2, 3000.0, 6000.0)
    assert row[18] == 12000.0
    assert "Cancelado" in {r[10] for r in rows}


def test_reexportar_reemplaza_la_pestana_y_actualiza_la_bitacora(
    admin, writer, create_order, period, db
):
    create_order()
    _export(admin, period)
    create_order()

    response = _export(admin, period)

    assert response.status_code == 200, response.text
    assert response.json()["orders_count"] == 2
    assert len(writer.sheets[(SHEET_ID, period)]["rows"]) == 2
    assert db.query(MonthlyArchive).count() == 1


def test_el_mes_usa_la_medianoche_de_bogota(admin, writer, create_order, period, db):
    """Un pedido de las 23:30 del último día del mes anterior no entra en este mes."""
    first_day = today_bogota().replace(day=1)
    late = create_order()
    db.get(Order, late["id_order"]).creation_datetime = datetime(
        first_day.year, first_day.month, first_day.day, 4, 30, tzinfo=UTC
    )  # 23:30 del día anterior en Bogotá
    db.commit()
    current = create_order()

    _export(admin, period)

    exported = {r[2] for r in writer.sheets[(SHEET_ID, period)]["rows"]}
    assert exported == {current["purchase_order"]}


def test_sin_spreadsheet_del_anio(admin, writer, create_order):
    create_order()

    response = _export(admin, f"{today_bogota():%Y-%m}")

    assert response.status_code == 422
    assert response.json()["code"] == "SPREADSHEET_NOT_CONFIGURED"
    assert writer.calls == 0


def test_mes_sin_pedidos(admin, writer, period):
    response = _export(admin, period)

    assert response.status_code == 422
    assert response.json()["code"] == "NO_ORDERS_TO_EXPORT"


def test_mes_futuro(admin, writer):
    next_month = today_bogota().replace(day=28) + timedelta(days=5)

    response = _export(admin, f"{next_month:%Y-%m}")

    assert response.status_code == 422
    assert response.json()["code"] == "MONTH_IN_FUTURE"


@pytest.mark.parametrize("bad", ["2026-13", "2026-1", "26-09", "septiembre"])
def test_formato_de_mes_invalido(admin, bad):
    assert _export(admin, bad).status_code == 422


def test_mes_ya_purgado(admin, writer, period, db, create_order):
    create_order()
    db.add(
        MonthlyArchive(
            archive_month=date.fromisoformat(f"{period}-01"),
            status=ArchiveStatus.PURGED,
            spreadsheet_id=SHEET_ID,
            sheet_title=period,
            orders_count=1,
            rows_count=1,
            total_sales=Decimal("1"),
            exported_at=datetime.now(UTC),
        )
    )
    db.commit()

    response = _export(admin, period)

    assert response.status_code == 409
    assert response.json()["code"] == "MONTH_ALREADY_PURGED"


def test_error_de_google_no_registra_nada(admin, writer, create_order, period, db):
    create_order()
    writer.fail = ExternalServiceError("Google Sheets", "sin acceso")

    response = _export(admin, period)

    assert response.status_code == 502
    assert db.query(MonthlyArchive).count() == 0


def test_verificacion_de_filas_fallida(admin, writer, create_order, period, db):
    create_order()
    writer.lose_rows = 1

    response = _export(admin, period)

    assert response.status_code == 502
    assert "verificación" in response.json()["detail"]
    assert db.query(MonthlyArchive).count() == 0


def test_solo_admin_exporta(client, writer, period):
    assert _export(client, period).status_code == 403
