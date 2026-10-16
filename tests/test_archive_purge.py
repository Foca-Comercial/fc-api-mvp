"""Archivado mensual (H5): purga de un mes fuera de la retención."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.core.timezone import BOGOTA_TZ
from app.models.coreModule.archive_spreadsheet import ArchiveSpreadsheet
from app.models.coreModule.client import Client
from app.models.coreModule.daily_order_counter import DailyOrderCounter
from app.models.coreModule.monthly_archive import MonthlyArchive
from app.models.coreModule.order import Order
from app.models.coreModule.order_detail import OrderDetail
from app.models.securityModule.user_session import UserSession
from app.services.coreModule.archive_service import add_months, first_retained_month
from app.utils.exceptions.business_exceptions import ExternalServiceError
from tests.helpers import API, item

SHEET_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-abc"


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def _move_to(db, order: dict, month) -> None:
    db.get(Order, order["id_order"]).creation_datetime = datetime.combine(
        month.replace(day=10), time(12, 0), tzinfo=BOGOTA_TZ
    )
    db.commit()


def _new_client_order(client, data, name) -> dict:
    response = client.post(
        f"{API}/orders/new-client",
        json={
            "client": {
                "name": name,
                "id_neighborhood": data.neighborhood.id_neighborhood,
            },
            "items": [item(data.products[0], 1)],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def old(db, admin, create_order, data):
    """Mes purgable (justo antes de la retención) con:
    - 2 pedidos de un cliente registrado (3 renglones en total)
    - 1 pedido de un cliente temporal que solo compró ese mes
    y, en el mes vigente, 1 pedido del cliente registrado y 1 de otro temporal."""
    month = add_months(first_retained_month(), -1)
    for year in {month.year, first_retained_month().year}:
        db.add(ArchiveSpreadsheet(year=year, spreadsheet_id=SHEET_ID))
    db.commit()

    old_orders = [
        create_order(items=[item(data.products[0], 1), item(data.products[1], 2)]),
        create_order(items=[item(data.products[2], 1)]),
    ]
    old_temp = _new_client_order(admin, data, "temporal viejo")
    for order in [*old_orders, old_temp]:
        _move_to(db, order, month)
    current = create_order()
    current_temp = _new_client_order(admin, data, "temporal actual")

    return SimpleNamespace(
        month=month,
        period=f"{month:%Y-%m}",
        old_orders=[*old_orders, old_temp],
        old_temp_client=old_temp["id_client"],
        current=current,
        current_temp_client=current_temp["id_client"],
    )


def _purge(client, period):
    return client.post(f"{API}/archive/{period}/purge")


def test_purga_reexporta_y_borra_solo_el_mes(admin, writer, db, data, old):
    orders_before = _count(db, Order)

    response = _purge(admin, old.period)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["deleted_orders"] == 3
    assert body["deleted_order_lines"] == 4
    assert body["archive"]["status"] == "PURGED"
    assert body["archive"]["id_user_purged"] == data.taker.id_user
    assert body["archive"]["purged_at"] is not None
    # La hoja quedó con el estado final antes de borrar
    assert len(writer.sheets[(SHEET_ID, old.period)]["rows"]) == 4

    db.expire_all()
    assert _count(db, Order) == orders_before - 3
    for order in old.old_orders:
        assert db.get(Order, order["id_order"]) is None
    assert db.get(Order, old.current["id_order"]) is not None
    remaining_lines = db.scalar(
        select(func.count())
        .select_from(OrderDetail)
        .where(OrderDetail.id_order.in_([o["id_order"] for o in old.old_orders]))
    )
    assert remaining_lines == 0  # ON DELETE CASCADE


def test_limpia_clientes_temporales_sin_pedidos(admin, writer, db, data, old):
    body = _purge(admin, old.period).json()

    db.expire_all()
    assert body["deleted_temporary_clients"] == 1
    assert db.get(Client, old.old_temp_client) is None
    assert db.get(Client, old.current_temp_client) is not None  # tiene pedido vigente
    assert db.get(Client, data.client.id_client) is not None  # registrado


def test_limpia_contadores_viejos_y_sesiones_vencidas(admin, writer, db, data, old):
    db.add(DailyOrderCounter(counter_date=old.month.replace(day=10), last_value=7))
    now = datetime.now(UTC)
    expired = UserSession(
        id_user=data.taker.id_user,
        refresh_token_hash="a" * 64,
        expires_at=now - timedelta(days=1),
    )
    active = UserSession(
        id_user=data.taker.id_user,
        refresh_token_hash="b" * 64,
        expires_at=now + timedelta(days=10),
        revoked=True,  # revocada pero vigente: se conserva
    )
    db.add_all([expired, active])
    db.commit()
    expired_id, active_id = expired.id_session, active.id_session
    counters_before = _count(db, DailyOrderCounter)

    body = _purge(admin, old.period).json()

    db.expire_all()
    assert body["deleted_order_counters"] == 1
    assert _count(db, DailyOrderCounter) == counters_before - 1  # el de hoy sigue
    assert body["deleted_expired_sessions"] >= 1
    assert db.get(UserSession, expired_id) is None
    assert db.get(UserSession, active_id) is not None


def test_no_se_purgan_meses_dentro_de_la_retencion(admin, writer, db, old):
    orders_before = _count(db, Order)

    response = _purge(admin, f"{first_retained_month():%Y-%m}")

    assert response.status_code == 422
    assert response.json()["code"] == "MONTH_WITHIN_RETENTION"
    assert writer.calls == 0
    assert _count(db, Order) == orders_before


def test_fallo_de_google_no_borra_nada(admin, writer, db, old):
    writer.fail = ExternalServiceError("Google Sheets", "sin acceso")
    orders_before = _count(db, Order)

    response = _purge(admin, old.period)

    assert response.status_code == 502
    assert _count(db, Order) == orders_before
    assert _count(db, MonthlyArchive) == 0


def test_verificacion_fallida_no_borra_nada(admin, writer, db, old):
    writer.lose_rows = 1
    orders_before = _count(db, Order)

    response = _purge(admin, old.period)

    assert response.status_code == 502
    assert _count(db, Order) == orders_before


def test_no_se_purga_ni_exporta_dos_veces(admin, writer, old):
    assert _purge(admin, old.period).status_code == 200

    again = _purge(admin, old.period)
    export = admin.post(f"{API}/archive/{old.period}/export")

    assert again.status_code == 409
    assert again.json()["code"] == "MONTH_ALREADY_PURGED"
    assert export.status_code == 409


def test_mes_sin_pedidos(admin, writer, db, old):
    empty = add_months(old.month, -1)
    db.merge(ArchiveSpreadsheet(year=empty.year, spreadsheet_id=SHEET_ID))
    db.commit()

    response = _purge(admin, f"{empty:%Y-%m}")

    assert response.status_code == 422
    assert response.json()["code"] == "NO_ORDERS_TO_EXPORT"


def test_bitacora_muestra_el_mes_purgado(admin, writer, old):
    _purge(admin, old.period)

    rows = admin.get(f"{API}/archive/").json()

    row = next(r for r in rows if r["month"] == old.period)
    assert (row["status"], row["orders_count"]) == ("PURGED", 3)
    assert Decimal(row["total_sales"]) > 0


def test_solo_admin_purga(client, writer):
    period = f"{add_months(first_retained_month(), -1):%Y-%m}"

    assert _purge(client, period).status_code == 403
