"""Archivo mensual: resumen de meses (GET /archive/months) para la vista del panel."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from app.core.timezone import BOGOTA_TZ, today_bogota
from app.models.coreModule.archive_spreadsheet import ArchiveSpreadsheet
from app.models.coreModule.monthly_archive import MonthlyArchive
from app.models.coreModule.order import Order
from app.services.coreModule.archive_service import add_months, first_retained_month
from app.utils.enums.archive_status import ArchiveStatus
from app.utils.enums.order_state import OrderState
from tests.helpers import API

URL = f"{API}/archive/months"
SHEET_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-abc"


def _label(month) -> str:
    return f"{month:%Y-%m}"


def _move_to(db, order: dict, month) -> None:
    row = db.get(Order, order["id_order"])
    row.creation_datetime = datetime.combine(
        month.replace(day=10), time(12, 0), tzinfo=BOGOTA_TZ
    )
    row.delivery_date = month.replace(day=10)
    db.commit()


def _sheet(db, *years) -> None:
    for year in set(years):
        db.add(ArchiveSpreadsheet(year=year, spreadsheet_id=SHEET_ID))
    db.commit()


def _months(admin) -> dict[str, dict]:
    response = admin.get(URL)
    assert response.status_code == 200, response.text
    return {row["month"]: row for row in response.json()["months"]}


def test_sin_pedidos(admin):
    body = admin.get(URL).json()

    assert body["months"] == []
    assert body["current_month"] == _label(today_bogota())
    assert body["first_retained_month"] == _label(first_retained_month())
    assert body["retention_months"] >= 1


def test_mes_vigente_se_exporta_pero_no_se_purga(admin, db, create_order):
    create_order()
    current = today_bogota().replace(day=1)

    without_sheet = _months(admin)[_label(current)]
    _sheet(db, current.year)
    with_sheet = _months(admin)[_label(current)]

    assert without_sheet["orders_count"] == 1
    assert without_sheet["retained"] is True
    assert without_sheet["spreadsheet_url"] is None
    assert without_sheet["can_export"] is False  # falta el spreadsheet del año
    assert with_sheet["can_export"] is True
    assert with_sheet["can_purge"] is False
    assert with_sheet["spreadsheet_url"].endswith(SHEET_ID)


def test_mes_viejo_sin_facturables_se_puede_purgar(admin, db, create_order):
    old = add_months(first_retained_month(), -1)
    _sheet(db, old.year)
    _move_to(db, create_order(), old)  # PENDING: no se factura, no exige cierre

    row = _months(admin)[_label(old)]

    assert row["retained"] is False
    assert row["unclosed_days"] == []
    assert (row["can_export"], row["can_purge"]) == (True, True)


def test_mes_viejo_con_dias_sin_cierre_no_se_purga(admin, db, create_order):
    old = add_months(first_retained_month(), -1)
    _sheet(db, old.year)
    order = create_order()
    assert admin.post(f"{API}/orders/{order['id_order']}/dispatch").status_code == 200
    _move_to(db, order, old)

    row = _months(admin)[_label(old)]

    assert row["unclosed_days"] == [old.replace(day=10).isoformat()]
    assert row["can_export"] is True
    assert row["can_purge"] is False


def test_ventas_sin_cancelados(admin, db, create_order):
    kept = create_order()
    cancelled = create_order()
    db.get(Order, cancelled["id_order"]).state = OrderState.CANCELLED
    db.commit()

    row = _months(admin)[_label(today_bogota())]

    assert row["orders_count"] == 2
    assert Decimal(row["total_sales"]) == Decimal(kept["order_total"])


def test_mes_purgado_aparece_sin_pedidos(admin, db):
    old = add_months(first_retained_month(), -2)
    _sheet(db, old.year)
    db.add(
        MonthlyArchive(
            archive_month=old,
            status=ArchiveStatus.PURGED,
            spreadsheet_id=SHEET_ID,
            sheet_title=_label(old),
            orders_count=40,
            rows_count=55,
            total_sales=Decimal("123000"),  # noqa: FURB157
            exported_at=datetime.now(UTC),
            purged_at=datetime.now(UTC),
        )
    )
    db.commit()

    row = _months(admin)[_label(old)]

    assert row["status"] == "PURGED"
    assert row["orders_count"] == 0
    assert row["exported_orders"] == 40
    assert (row["can_export"], row["can_purge"]) == (False, False)


def test_no_incluye_meses_futuros(admin, db, create_order):
    next_month = add_months(today_bogota().replace(day=1), 1)
    order = create_order(delivery_date=(today_bogota() + timedelta(days=1)).isoformat())
    row = db.get(Order, order["id_order"])
    row.delivery_date = next_month.replace(day=2)
    db.commit()

    assert _label(next_month) not in _months(admin)


def test_orden_del_mas_reciente_al_mas_antiguo(admin, db, create_order):
    old = add_months(first_retained_month(), -1)
    create_order()
    _move_to(db, create_order(), old)

    months = [row["month"] for row in admin.get(URL).json()["months"]]

    assert months == [_label(today_bogota()), _label(old)]


def test_solo_admin(client):
    assert client.get(URL).status_code == 403
