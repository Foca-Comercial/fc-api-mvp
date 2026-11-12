"""Cancelación de pedidos (cambio final B3): POST /orders/{id}/cancel."""

import pytest

from app.models.coreModule.order import Order
from tests.helpers import API


def _cancel(client, id_order: int, **body):
    payload = {"cancel_reason": "CLIENT_ABSENT", **body}
    return client.post(f"{API}/orders/{id_order}/cancel", json=payload)


def test_cancela_pedido_pendiente_con_motivo_y_auditoria(client, create_order, db, data):
    order = create_order()

    response = _cancel(client, order["id_order"], cancel_note="  No abrió  ")

    assert response.status_code == 200, response.text
    assert response.json()["state"] == "CANCELLED"
    row = db.get(Order, order["id_order"])
    assert row.cancel_reason.value == "CLIENT_ABSENT"
    assert row.cancel_note == "No abrió"
    assert row.cancelled_at is not None
    assert row.id_user_canceller == data.taker.id_user
    # No borra nada: conserva el PO y los productos
    assert row.purchase_order == order["purchase_order"]
    assert len(row.order_details) == 1


def test_cancela_pedido_despachado_y_conserva_la_hora_de_despacho(client, create_order, db):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    response = _cancel(client, order["id_order"], cancel_reason="DAMAGED_PRODUCT")

    assert response.status_code == 200, response.text
    assert response.json()["dispatch_time"] is not None
    assert db.get(Order, order["id_order"]).cancel_note is None


@pytest.mark.parametrize("final_state", ["DELIVERED", "CANCELLED"])
def test_no_cancela_pedidos_entregados_ni_cancelados(client, create_order, final_state):
    order = create_order()
    if final_state == "DELIVERED":
        client.post(f"{API}/orders/{order['id_order']}/dispatch")
        client.post(f"{API}/orders/{order['id_order']}/deliver")
    else:
        _cancel(client, order["id_order"])

    response = _cancel(client, order["id_order"], cancel_reason="OTHER")

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "ORDER_NOT_CANCELLABLE"


def test_motivo_obligatorio_y_de_la_lista(client, create_order):
    order = create_order()
    url = f"{API}/orders/{order['id_order']}/cancel"

    assert client.post(url, json={}).status_code == 422
    assert client.post(url, json={"cancel_reason": "SE_ARREPINTIO"}).status_code == 422


def test_nota_maximo_300_caracteres(client, create_order):
    order = create_order()

    response = _cancel(client, order["id_order"], cancel_note="x" * 301)

    assert response.status_code == 422


def test_pedido_inexistente(client):
    assert _cancel(client, 999999999).status_code == 404


def test_detalle_muestra_la_cancelacion(client, create_order):
    order = create_order()
    _cancel(client, order["id_order"], cancel_note="Llamó a cancelar")

    detail = client.get(f"{API}/orders/{order['id_order']}/details").json()

    assert detail["cancel_reason"] == "CLIENT_ABSENT"
    assert detail["cancel_note"] == "Llamó a cancelar"
    assert detail["canceller_name"] == "Ana Gestora"
    assert detail["cancelled_at"] is not None


def test_cancelado_queda_en_el_tablero_de_pendientes(client, create_order):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")
    _cancel(client, order["id_order"])

    pending = client.get(f"{API}/orders/dashboard-summary").json()
    dispatched = client.get(f"{API}/orders/dispatched-summary").json()

    assert order["id_order"] in {r["id_order"] for r in pending}
    assert order["id_order"] not in {r["id_order"] for r in dispatched}


def test_despachado_cancelado_cuenta_en_el_resumen_del_cierre(client, create_order):
    dispatched = create_order()
    client.post(f"{API}/orders/{dispatched['id_order']}/dispatch")
    _cancel(client, dispatched["id_order"])
    pending = create_order()
    _cancel(client, pending["id_order"])

    cards = client.get(f"{API}/shifts_closures/summary").json()["cards"]

    assert cards["cancelled"] == 2
    assert cards["cancelled_after_dispatch"] == 1  # solo el que ya había salido
