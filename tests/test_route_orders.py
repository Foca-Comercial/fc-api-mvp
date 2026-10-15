"""Pedidos por ruta (R4): rutas del día, precarga y creación en lote."""

from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select, text

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.order import Order
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.models.parametersModule.route import Route
from app.utils.enums.order_state import OrderState
from tests.helpers import API, item

MONDAY = date(2026, 10, 12)
TUESDAY = date(2026, 10, 13)


def _today(db) -> date:
    return db.scalar(text("SELECT (now() AT TIME ZONE 'America/Bogota')::date"))


def _order_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Order))


@pytest.fixture()
def route(db, data):
    """Ruta activa que sale lunes, jueves y HOY, con:
    - data.client (registrado, con precio especial en el producto 0)
    - otro cliente registrado
    - un cliente temporal y uno inactivo asignados directamente (no se les
      toma pedido desde la ruta)."""
    days = sorted({1, 4, _today(db).isoweekday()})
    route = Route(name="RUTA PEDIDOS", days_week=days, departure_time=time(6, 30))
    other = Client(
        name="OTRO REGISTRADO",
        id_neighborhood=data.neighborhood.id_neighborhood,
        is_registered=True,
    )
    temporary = Client(
        name="CLIENTE DE PASO", id_neighborhood=data.neighborhood.id_neighborhood
    )
    inactive = Client(
        name="REGISTRADO INACTIVO",
        id_neighborhood=data.neighborhood.id_neighborhood,
        is_registered=True,
        active=False,
    )
    db.add_all([route, other, temporary, inactive])
    db.flush()
    db.add_all(
        [
            ClientRoute(id_route=route.id_route, id_client=c.id_client)
            for c in (data.client, other, temporary, inactive)
        ]
        + [
            SpecialCustomerPrice(
                id_client=data.client.id_client,
                id_product=data.products[0].id_product,
                agreed_price=Decimal("2500.00"),
            )
        ]
    )
    db.commit()
    return SimpleNamespace(
        route=route, registered=data.client, other=other, temporary=temporary
    )


def _batch(client, id_route, orders, **extra):
    return client.post(
        f"{API}/orders/routes/{id_route}", json={"orders": orders, **extra}
    )


# --- Rutas del día -----------------------------------------------------------------


def test_rutas_del_dia_segun_dia_de_la_semana(client, route, db):
    other_day = Route(name="SOLO MARTES", days_week=[2], departure_time=time(8, 0))
    inactive = Route(
        name="INACTIVA LUNES", days_week=[1], departure_time=time(9, 0), active=False
    )
    db.add_all([other_day, inactive])
    db.commit()

    monday = client.get(f"{API}/orders/routes-of-day?target_date={MONDAY}").json()
    tuesday = client.get(f"{API}/orders/routes-of-day?target_date={TUESDAY}").json()

    monday_ids = {r["id_route"] for r in monday}
    assert route.route.id_route in monday_ids
    assert other_day.id_route not in monday_ids
    assert inactive.id_route not in monday_ids
    assert other_day.id_route in {r["id_route"] for r in tuesday}

    row = next(r for r in monday if r["id_route"] == route.route.id_route)
    assert row["clients_count"] == 2  # sin el temporal ni el inactivo
    assert row["orders_count"] == 0


def test_rutas_del_dia_por_defecto_es_hoy(client, route):
    response = client.get(f"{API}/orders/routes-of-day")

    assert response.status_code == 200, response.text
    assert route.route.id_route in {r["id_route"] for r in response.json()}


# --- Precarga ------------------------------------------------------------------------


def test_precarga_trae_clientes_de_la_ruta_con_su_precio(client, route, data):
    response = client.get(f"{API}/orders/routes/{route.route.id_route}/template")

    assert response.status_code == 200, response.text
    template = response.json()
    assert len(template["products"]) == 3
    clients = {c["id_client"]: c for c in template["clients"]}
    assert set(clients) == {route.registered.id_client, route.other.id_client}

    p0 = data.products[0].id_product
    special = next(
        p for p in clients[route.registered.id_client]["prices"] if p["id_product"] == p0
    )
    regular = next(
        p for p in clients[route.other.id_client]["prices"] if p["id_product"] == p0
    )
    assert (Decimal(special["unit_price"]), special["is_special"]) == (
        Decimal("2500.00"),
        True,
    )
    assert (Decimal(regular["unit_price"]), regular["is_special"]) == (
        Decimal("3000.00"),
        False,
    )
    assert all(c["existing_order_id"] is None for c in template["clients"])


def test_precarga_de_ruta_inexistente(client):
    assert client.get(f"{API}/orders/routes/999999/template").status_code == 404


# --- Creación en lote ------------------------------------------------------------------


def test_crea_los_pedidos_de_la_ruta_en_lote(client, route, data, db):
    p0, p1, _ = data.products
    response = _batch(
        client,
        route.route.id_route,
        [
            {"id_client": route.registered.id_client, "items": [item(p0, 4, "2500.00")]},
            {"id_client": route.other.id_client, "items": [item(p0, 1), item(p1, 2)]},
        ],
        estimated_delivery="10:00",
        id_user_vehicle=data.user_vehicle.id_user_vehicle,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["created"] == 2
    orders = {o["id_client"]: o for o in body["orders"]}
    first, second = orders[route.registered.id_client], orders[route.other.id_client]
    assert Decimal(first["order_total"]) == Decimal("10000.00")
    assert Decimal(second["order_total"]) == Decimal("15000.00")
    assert {o["id_route"] for o in body["orders"]} == {route.route.id_route}
    assert {o["id_user_vehicle"] for o in body["orders"]} == {
        data.user_vehicle.id_user_vehicle
    }
    assert {o["id_user_taker"] for o in body["orders"]} == {data.taker.id_user}
    assert {o["state"] for o in body["orders"]} == {"PENDING"}
    numbers = sorted(int(o["purchase_order"]) for o in body["orders"])
    assert numbers[1] == numbers[0] + 1  # consecutivo del día

    # Aparecen en la tabla principal y en la precarga/rutas del día
    dashboard = {r["id_order"] for r in client.get(f"{API}/orders/dashboard-summary").json()}
    assert {first["id_order"], second["id_order"]} <= dashboard
    template = client.get(f"{API}/orders/routes/{route.route.id_route}/template").json()
    existing = {c["id_client"]: c["existing_order_id"] for c in template["clients"]}
    assert existing[route.registered.id_client] == first["id_order"]
    today = client.get(f"{API}/orders/routes-of-day?target_date={_today(db)}").json()
    row = next(r for r in today if r["id_route"] == route.route.id_route)
    assert row["orders_count"] == 2


def test_no_se_genera_dos_veces_el_mismo_cliente_de_la_ruta(client, route, data, db):
    p0 = data.products[0]
    first = _batch(
        client,
        route.route.id_route,
        [{"id_client": route.registered.id_client, "items": [item(p0, 1)]}],
    )
    assert first.status_code == 201, first.text
    before = _order_count(db)

    second = _batch(
        client,
        route.route.id_route,
        [
            {"id_client": route.other.id_client, "items": [item(p0, 1)]},
            {"id_client": route.registered.id_client, "items": [item(p0, 2)]},
        ],
    )

    assert second.status_code == 409
    assert second.json()["code"] == "ROUTE_ORDER_EXISTS"
    assert _order_count(db) == before  # tampoco se creó el del otro cliente


def test_un_pedido_cancelado_no_bloquea_volver_a_generarlo(client, route, data, db):
    p0 = data.products[0]
    created = _batch(
        client,
        route.route.id_route,
        [{"id_client": route.registered.id_client, "items": [item(p0, 1)]}],
    ).json()
    db.get(Order, created["orders"][0]["id_order"]).state = OrderState.CANCELLED
    db.commit()

    again = _batch(
        client,
        route.route.id_route,
        [{"id_client": route.registered.id_client, "items": [item(p0, 1)]}],
    )

    assert again.status_code == 201, again.text


@pytest.mark.parametrize("who", ["temporary", "outsider"])
def test_solo_clientes_de_la_ruta(client, route, data, db, who):
    outsider = Client(
        name="NO ASIGNADO",
        id_neighborhood=data.neighborhood.id_neighborhood,
        is_registered=True,
    )
    db.add(outsider)
    db.commit()
    target = route.temporary if who == "temporary" else outsider
    before = _order_count(db)

    response = _batch(
        client,
        route.route.id_route,
        [
            {"id_client": route.registered.id_client, "items": [item(data.products[0], 1)]},
            {"id_client": target.id_client, "items": [item(data.products[0], 1)]},
        ],
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CLIENT_NOT_IN_ROUTE"
    assert _order_count(db) == before


def test_cliente_repetido_en_la_lista(client, route, data):
    rows = [{"id_client": route.registered.id_client, "items": [item(data.products[0], 1)]}]

    response = _batch(client, route.route.id_route, rows * 2)

    assert response.status_code == 422
    assert response.json()["code"] == "DUPLICATE_CLIENT"


def test_error_en_un_cliente_no_crea_ninguno_ni_consume_numeros(client, route, data, db):
    p0 = data.products[0]
    before = _order_count(db)

    failed = _batch(
        client,
        route.route.id_route,
        [
            {"id_client": route.registered.id_client, "items": [item(p0, 1)]},
            {
                "id_client": route.other.id_client,
                "items": [{"id_product": 999_999, "cant": 1, "unit_price": "1"}],
            },
        ],
    )

    assert failed.status_code == 422
    assert failed.json()["field"] == "id_product"
    assert f"Cliente {route.other.id_client}" in failed.json()["detail"]
    assert _order_count(db) == before

    ok = _batch(
        client,
        route.route.id_route,
        [{"id_client": route.registered.id_client, "items": [item(p0, 1)]}],
    )
    assert ok.json()["orders"][0]["purchase_order"] == "001"


def test_ruta_inactiva_no_genera_pedidos(client, route, data, db):
    route.route.active = False
    db.commit()

    response = _batch(
        client,
        route.route.id_route,
        [{"id_client": route.registered.id_client, "items": [item(data.products[0], 1)]}],
    )

    assert response.status_code == 422
    assert response.json()["code"] == "ROUTE_INACTIVE"


def test_lista_vacia_se_rechaza(client, route):
    assert _batch(client, route.route.id_route, []).status_code == 422
