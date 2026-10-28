"""Pedidos programados: delivery_date (día de entrega) distinto al de creación."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.timezone import today_bogota
from app.models.coreModule.client import Client
from app.models.coreModule.order import Order
from app.services.coreModule.order_service import MAX_SCHEDULE_DAYS
from tests.helpers import API, item


@pytest.fixture()
def tomorrow():
    return today_bogota() + timedelta(days=1)


def _ids(response) -> list[int]:
    assert response.status_code == 200, response.text
    return [row["id_order"] for row in response.json()]


# --- Creación ---------------------------------------------------------------------


def test_sin_fecha_el_pedido_es_de_hoy(create_order):
    order = create_order()

    assert order["delivery_date"] == today_bogota().isoformat()


def test_programar_un_pedido_para_otro_dia(create_order, tomorrow):
    order = create_order(delivery_date=tomorrow.isoformat())

    assert order["delivery_date"] == tomorrow.isoformat()
    # creation_datetime sigue siendo el instante real en que se tomó
    assert order["creation_datetime"] is not None


def test_no_se_programa_en_el_pasado(client, data):
    yesterday = today_bogota() - timedelta(days=1)

    response = client.post(
        f"{API}/orders/existing-client",
        json={
            "id_client": data.client.id_client,
            "delivery_date": yesterday.isoformat(),
            "items": [item(data.products[0], 1)],
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "DELIVERY_DATE_IN_PAST"
    assert response.json()["field"] == "delivery_date"


def test_horizonte_maximo_de_programacion(client, data):
    limit = today_bogota() + timedelta(days=MAX_SCHEDULE_DAYS)
    body = {"id_client": data.client.id_client, "items": [item(data.products[0], 1)]}

    ok = client.post(
        f"{API}/orders/existing-client", json={**body, "delivery_date": str(limit)}
    )
    too_far = client.post(
        f"{API}/orders/existing-client",
        json={**body, "delivery_date": str(limit + timedelta(days=1))},
    )

    assert ok.status_code == 201, ok.text
    assert too_far.status_code == 422
    assert too_far.json()["code"] == "DELIVERY_DATE_TOO_FAR"


def test_cliente_nuevo_con_fecha_invalida_no_crea_el_cliente(client, data, db):
    before = db.scalar(select(func.count()).select_from(Client))

    response = client.post(
        f"{API}/orders/new-client",
        json={
            "client": {
                "name": "cliente programado",
                "id_neighborhood": data.neighborhood.id_neighborhood,
            },
            "delivery_date": str(today_bogota() - timedelta(days=2)),
            "items": [item(data.products[0], 1)],
        },
    )

    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(Client)) == before


# --- Tablero ----------------------------------------------------------------------


def test_el_pedido_programado_sale_el_dia_de_entrega_no_antes(
    client, create_order, tomorrow
):
    today_order = create_order()
    scheduled = create_order(delivery_date=tomorrow.isoformat())

    today_ids = _ids(client.get(f"{API}/orders/dashboard-summary"))
    tomorrow_ids = _ids(
        client.get(f"{API}/orders/dashboard-summary?target_date={tomorrow}")
    )

    assert today_order["id_order"] in today_ids
    assert scheduled["id_order"] not in today_ids
    assert scheduled["id_order"] in tomorrow_ids
    assert today_order["id_order"] not in tomorrow_ids


# --- Consecutivo ------------------------------------------------------------------


def test_el_consecutivo_va_por_dia_de_entrega(create_order, tomorrow):
    scheduled = create_order(delivery_date=tomorrow.isoformat())
    scheduled_2 = create_order(delivery_date=tomorrow.isoformat())
    today_order = create_order()

    # Los de mañana llevan su propia secuencia; no consumen la de hoy
    assert int(scheduled_2["purchase_order"]) == int(scheduled["purchase_order"]) + 1
    assert int(today_order["purchase_order"]) >= 1
    assert scheduled["purchase_order"] == "001"


# --- Cierre -----------------------------------------------------------------------


def test_el_cierre_de_hoy_no_cuenta_los_pedidos_programados(
    client, create_order, tomorrow
):
    create_order()
    create_order(delivery_date=tomorrow.isoformat())

    response = client.get(f"{API}/shifts_closures/summary")

    assert response.status_code == 200, response.text
    cards = response.json()["cards"]
    assert (cards["total_orders"], cards["pending"]) == (1, 1)


# --- Despacho ---------------------------------------------------------------------


def test_no_se_despacha_un_pedido_programado_a_futuro(client, create_order, tomorrow):
    order = create_order(delivery_date=tomorrow.isoformat())

    response = client.post(f"{API}/orders/{order['id_order']}/dispatch")

    assert response.status_code == 422
    assert response.json()["code"] == "ORDER_SCHEDULED"


def test_un_pedido_de_hoy_se_despacha_normal(client, create_order):
    order = create_order()

    response = client.post(f"{API}/orders/{order['id_order']}/dispatch")

    assert response.status_code == 200, response.text


# --- Reprogramación ---------------------------------------------------------------


def test_reprogramar_cambia_el_dia_y_renumera(client, create_order, tomorrow, db):
    order = create_order()
    other = create_order(delivery_date=tomorrow.isoformat())  # 001 de mañana

    response = client.patch(
        f"{API}/orders/{order['id_order']}", json={"delivery_date": str(tomorrow)}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["delivery_date"] == tomorrow.isoformat()
    # Recibe el siguiente número del día de destino: no repite el del otro pedido
    assert int(body["purchase_order"]) == int(other["purchase_order"]) + 1
    db.expire_all()
    assert db.get(Order, order["id_order"]).delivery_date == tomorrow


def test_reprogramar_a_la_misma_fecha_no_renumera(client, create_order):
    order = create_order()

    response = client.patch(
        f"{API}/orders/{order['id_order']}",
        json={"delivery_date": order["delivery_date"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["purchase_order"] == order["purchase_order"]


def test_reprogramar_valida_la_fecha(client, create_order):
    order = create_order()
    past = (today_bogota() - timedelta(days=1)).isoformat()

    in_past = client.patch(
        f"{API}/orders/{order['id_order']}", json={"delivery_date": past}
    )
    no_null = client.patch(
        f"{API}/orders/{order['id_order']}", json={"delivery_date": None}
    )

    assert in_past.status_code == 422
    assert in_past.json()["code"] == "DELIVERY_DATE_IN_PAST"
    assert no_null.status_code == 422
    assert no_null.json()["code"] == "DELIVERY_DATE_REQUIRED"


def test_no_se_reprograma_un_pedido_despachado(client, create_order, tomorrow):
    order = create_order()
    assert client.post(f"{API}/orders/{order['id_order']}/dispatch").status_code == 200

    response = client.patch(
        f"{API}/orders/{order['id_order']}", json={"delivery_date": str(tomorrow)}
    )

    assert response.status_code == 422
    assert response.json()["field"] == "delivery_date"


# --- Detalle ----------------------------------------------------------------------


def test_el_detalle_trae_la_fecha_de_entrega(client, create_order, tomorrow):
    order = create_order(delivery_date=tomorrow.isoformat())

    response = client.get(f"{API}/orders/{order['id_order']}/details")

    assert response.status_code == 200, response.text
    assert response.json()["delivery_date"] == tomorrow.isoformat()
