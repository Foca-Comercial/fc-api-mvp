"""Despacho múltiple (cambio final B6): POST /orders/dispatch-batch, todo o nada."""

from datetime import timedelta

from app.core.timezone import today_bogota
from app.models.coreModule.order import Order
from tests.helpers import API, mark_cancelled

URL = f"{API}/orders/dispatch-batch"


def test_despacha_todos_con_la_misma_hora(client, create_order, db):
    orders = [create_order() for _ in range(3)]
    ids = [o["id_order"] for o in orders]

    response = client.post(URL, json={"ids": ids})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dispatched"] == 3
    assert [o["id_order"] for o in body["orders"]] == sorted(ids)
    assert {o["state"] for o in body["orders"]} == {"DISPATCHED"}
    assert len({o["dispatch_time"] for o in body["orders"]}) == 1


def test_pedidos_sin_cd_se_despachan_igual(client, create_order):
    transfer = create_order(payment_method="TRANSFER")
    cash = create_order()

    response = client.post(
        URL, json={"ids": [transfer["id_order"], cash["id_order"]]}
    )

    assert response.status_code == 200, response.text
    assert response.json()["dispatched"] == 2


def test_todo_o_nada_si_uno_no_esta_pendiente(client, create_order, db):
    pending = create_order()
    dispatched = create_order()
    client.post(f"{API}/orders/{dispatched['id_order']}/dispatch")
    cancelled = create_order()
    mark_cancelled(db, cancelled["id_order"])
    db.flush()

    response = client.post(
        URL,
        json={
            "ids": [pending["id_order"], dispatched["id_order"], cancelled["id_order"]]
        },
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "ORDER_BATCH_NOT_DISPATCHABLE"
    failed = {d["purchase_order"] for d in body["details"]}
    assert failed == {dispatched["purchase_order"], cancelled["purchase_order"]}
    assert all(d["reason"] for d in body["details"])
    # El pendiente válido tampoco se despachó
    assert db.get(Order, pending["id_order"]).state.value == "PENDING"


def test_no_despacha_pedidos_programados_a_futuro(client, create_order, db):
    tomorrow = today_bogota() + timedelta(days=1)
    today = create_order()
    scheduled = create_order(delivery_date=tomorrow.isoformat())

    response = client.post(
        URL, json={"ids": [today["id_order"], scheduled["id_order"]]}
    )

    assert response.status_code == 422, response.text
    details = response.json()["details"]
    assert [d["id_order"] for d in details] == [scheduled["id_order"]]
    assert db.get(Order, today["id_order"]).state.value == "PENDING"


def test_pedido_inexistente_sale_en_el_detalle(client, create_order):
    order = create_order()

    response = client.post(URL, json={"ids": [order["id_order"], 999999999]})

    assert response.status_code == 422, response.text
    details = response.json()["details"]
    assert details == [
        {"id_order": 999999999, "purchase_order": None, "reason": "El pedido no existe."}
    ]


def test_rechaza_lista_vacia_o_con_repetidos(client, create_order):
    order = create_order()

    assert client.post(URL, json={"ids": []}).status_code == 422
    repeated = client.post(URL, json={"ids": [order["id_order"], order["id_order"]]})
    assert repeated.status_code == 422


def test_otros_errores_no_traen_details(client, create_order):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    response = client.post(f"{API}/orders/{order['id_order']}/dispatch")

    assert response.status_code == 422
    assert "details" not in response.json()
