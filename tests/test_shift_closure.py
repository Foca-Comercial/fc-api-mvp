"""Vista de Cierre: CRUD de solo lectura (C1) y resumen del día (C2)."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.timezone import BOGOTA_TZ, today_bogota
from app.models.coreModule.order import Order
from app.models.coreModule.shift_closure import ShiftClosure
from app.utils.enums.order_state import OrderState
from tests.helpers import API, item

URL = f"{API}/shifts_closures"


def test_el_crud_es_de_solo_lectura(admin):
    assert admin.get(f"{URL}/").status_code == 200
    assert admin.post(f"{URL}/", json={}).status_code == 405
    assert admin.patch(f"{URL}/1", json={}).status_code == 405
    assert admin.delete(f"{URL}/1").status_code == 405


def test_un_cierre_por_vendedor_y_dia(db, data):
    def closure():
        return ShiftClosure(
            closure_date=date(2026, 10, 15),
            id_user_vehicle=data.user_vehicle.id_user_vehicle,
            total_orders=1,
            total_sales=Decimal("1000"),
        )

    db.add(closure())
    db.flush()
    db.add(closure())

    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- Resumen del cierre (C2): GET /shifts_closures/summary ---------------------------

SUMMARY = f"{URL}/summary"


def _dispatch(client, order: dict, deliver: bool = False) -> None:
    response = client.post(f"{API}/orders/{order['id_order']}/dispatch")
    assert response.status_code == 200, response.text
    if deliver:
        response = client.post(f"{API}/orders/{order['id_order']}/deliver")
        assert response.status_code == 200, response.text


def _move(db, order: dict, day: date) -> None:
    db.get(Order, order["id_order"]).creation_datetime = datetime.combine(
        day, time(10, 0), tzinfo=BOGOTA_TZ
    )
    db.commit()


def _summary(client, day: date | None = None) -> dict:
    url = SUMMARY if day is None else f"{SUMMARY}?target_date={day}"
    response = client.get(url)
    assert response.status_code == 200, response.text
    return response.json()


def test_resumen_consolida_por_vendedor_y_cuenta_estados(
    client, create_order, db, data, default_seller
):
    driver = data.user_vehicle.id_user_vehicle
    p0, p1, p2 = data.products
    a = create_order(items=[item(p0, 2), item(p1, 1)], id_user_vehicle=driver)  # 12000
    b = create_order(items=[item(p0, 1, "2500.00")], id_user_vehicle=driver)  # 2500
    c = create_order(items=[item(p2, 1)])  # 8000, sin conductor
    create_order(id_user_vehicle=driver)  # queda pendiente
    cancelled = create_order(id_user_vehicle=driver)
    _dispatch(client, a)
    _dispatch(client, b, deliver=True)
    _dispatch(client, c)
    db.get(Order, cancelled["id_order"]).state = OrderState.CANCELLED
    db.commit()

    body = _summary(client)

    assert body["closure_date"] == today_bogota().isoformat()
    cards = body["cards"]
    assert (cards["total_orders"], cards["pending"], cards["cancelled"]) == (5, 1, 1)
    assert (cards["dispatched"], cards["delivered"]) == (2, 1)
    assert cards["sellers_count"] == 2
    assert Decimal(cards["total_income"]) == Decimal("22500")
    assert body["exported"] is False

    default_row, driver_row = body["sellers"]  # ordenados por código: 9, 99
    assert (default_row["seller_code"], default_row["seller_name"]) == (9, "Hielo Foca")
    assert default_row["orders_count"] == default_row["unassigned_orders"] == 1
    assert default_row["products"] == [
        {"product_code": "Z93", "product_name": "BOTELLON AGUA", "quantity": 1}
    ]
    assert Decimal(default_row["total_sales"]) == Decimal("8000")

    assert (driver_row["seller_code"], driver_row["seller_name"]) == (
        99,
        "Carlos Conductor",
    )
    assert (driver_row["orders_count"], driver_row["unassigned_orders"]) == (2, 0)
    # Z91 a dos precios distintos se suma en una sola cantidad
    assert [(p["product_code"], p["quantity"]) for p in driver_row["products"]] == [
        ("Z91", 3),
        ("Z92", 1),
    ]
    assert driver_row["total_quantity"] == 4
    assert Decimal(driver_row["total_sales"]) == Decimal("14500")
    assert driver_row["exported_at"] is None


def test_sin_conductor_se_suma_a_los_pedidos_propios_del_vendedor_por_defecto(
    client, create_order, data, default_seller
):
    own = create_order(id_user_vehicle=default_seller.id_user_vehicle)  # 2 x Z91
    unassigned = create_order()  # 2 x Z91, sin conductor
    _dispatch(client, own)
    _dispatch(client, unassigned)

    (row,) = _summary(client)["sellers"]

    assert row["id_user_vehicle"] == default_seller.id_user_vehicle
    assert (row["orders_count"], row["unassigned_orders"]) == (2, 1)
    assert row["products"][0]["quantity"] == 4
    assert Decimal(row["total_sales"]) == Decimal("12000")


def test_sin_vendedor_por_defecto_responde_422_solo_si_hace_falta(
    client, create_order, data, monkeypatch
):
    monkeypatch.setattr(settings, "DEFAULT_SELLER_CODE", "98")  # no existe
    _dispatch(client, create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle))

    assert client.get(SUMMARY).status_code == 200  # todos tienen conductor

    _dispatch(client, create_order())
    response = client.get(SUMMARY)

    assert response.status_code == 422
    assert response.json()["code"] == "DEFAULT_SELLER_MISSING"


def test_resumen_de_otro_dia_y_fecha_futura(client, create_order, db, data):
    yesterday = today_bogota() - timedelta(days=1)
    order = create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle)
    _dispatch(client, order)
    _move(db, order, yesterday)

    assert _summary(client)["sellers"] == []
    assert _summary(client, yesterday)["cards"]["dispatched"] == 1

    response = client.get(f"{SUMMARY}?target_date={today_bogota() + timedelta(days=1)}")
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_CLOSURE_DATE"


def test_dia_sin_pedidos(client):
    body = _summary(client, date(2020, 1, 15))

    assert body["sellers"] == []
    assert body["exported"] is False
    assert body["cards"]["total_orders"] == 0
    assert Decimal(body["cards"]["total_income"]) == 0


def test_estado_de_exportacion_y_cambios_posteriores(client, create_order, db, data):
    driver = data.user_vehicle.id_user_vehicle
    _dispatch(client, create_order(id_user_vehicle=driver))  # 6000
    db.add(
        ShiftClosure(
            closure_date=today_bogota(),
            id_user_vehicle=driver,
            total_orders=1,
            total_sales=Decimal("6000"),
            exported_siigo=True,
            exported_at=datetime.now(UTC),
        )
    )
    db.commit()

    body = _summary(client)
    assert body["exported"] is True
    assert body["sellers"][0]["exported_at"] is not None
    assert body["sellers"][0]["export_outdated"] is False

    _dispatch(client, create_order(id_user_vehicle=driver))  # llega otro pedido

    body = _summary(client)
    assert body["exported"] is False
    assert body["sellers"][0]["export_outdated"] is True


def test_codigo_de_vendedor_no_numerico_responde_422(client, create_order, db, data):
    data.user_vehicle.code = "AB"  # dato antiguo: el schema ya no lo permite
    db.commit()
    _dispatch(client, create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle))

    response = client.get(SUMMARY)

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SELLER_CODE"


def test_el_resumen_es_del_gestor_y_del_admin(admin):
    assert admin.get(SUMMARY).status_code == 200
