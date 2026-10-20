"""Consultas de pedidos para la UI: detalle, comprobante PDF y dashboards."""

from datetime import UTC, datetime

from app.models.coreModule.order import Order
from tests.helpers import API

# --- Detalle y comprobante (regresión bug 1) --------------------------------------


def test_detalle_de_pedido_sin_conductor(client, create_order):
    order = create_order()

    response = client.get(f"{API}/orders/{order['id_order']}/details")

    assert response.status_code == 200, response.text
    assert response.json()["driver_code"] is None
    assert response.json()["driver_name"] is None
    assert len(response.json()["items"]) == 1


def test_detalle_de_pedido_con_conductor(client, create_order, data):
    order = create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle)

    response = client.get(f"{API}/orders/{order['id_order']}/details")

    assert response.status_code == 200, response.text
    assert response.json()["driver_code"] == "99"
    assert response.json()["driver_name"] == "Carlos Conductor"


def test_comprobante_requiere_pedido_despachado(client, create_order):
    order = create_order()

    response = client.get(f"{API}/orders/{order['id_order']}/receipt")

    assert response.status_code == 422


def test_comprobante_de_pedido_despachado_sin_conductor(client, create_order):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    response = client.get(f"{API}/orders/{order['id_order']}/receipt")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


# --- Dashboards (paso 5) ------------------------------------------------------------


def _ids(response) -> set[int]:
    assert response.status_code == 200, response.text
    return {row["id_order"] for row in response.json()}


def test_dashboard_separa_pendientes_de_despachados(client, create_order):
    pending = create_order()
    dispatched = create_order()
    client.post(f"{API}/orders/{dispatched['id_order']}/dispatch")

    main = _ids(client.get(f"{API}/orders/dashboard-summary"))
    sent = _ids(client.get(f"{API}/orders/dispatched-summary"))

    assert pending["id_order"] in main
    assert dispatched["id_order"] not in main
    assert dispatched["id_order"] in sent
    assert pending["id_order"] not in sent


def test_pedido_entregado_sigue_en_vista_de_despachados(client, create_order):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")
    client.post(f"{API}/orders/{order['id_order']}/deliver")

    sent = client.get(f"{API}/orders/dispatched-summary")

    assert order["id_order"] in _ids(sent)
    row = next(r for r in sent.json() if r["id_order"] == order["id_order"])
    assert row["state"] == "DELIVERED"


# --- Zona horaria (regresión bug 3) ------------------------------------------------


def test_dashboard_usa_el_dia_y_la_hora_de_bogota(client, create_order, db):
    """04:30 UTC del 15 de octubre = 23:30 del 14 de octubre en Bogotá (UTC-5)."""
    order = create_order()
    db.get(Order, order["id_order"]).creation_datetime = datetime(
        2026, 10, 15, 4, 30, tzinfo=UTC
    )
    db.flush()

    day_14 = client.get(f"{API}/orders/dashboard-summary?target_date=2026-10-14")
    day_15 = client.get(f"{API}/orders/dashboard-summary?target_date=2026-10-15")

    assert order["id_order"] in _ids(day_14)
    assert order["id_order"] not in _ids(day_15)
    row = next(r for r in day_14.json() if r["id_order"] == order["id_order"])
    assert row["creation_time"] == "23:30"


def test_dashboard_incluye_hora_estimada(client, create_order):
    order = create_order(estimated_delivery="14:30:00")

    rows = client.get(f"{API}/orders/dashboard-summary").json()
    row = next(r for r in rows if r["id_order"] == order["id_order"])

    assert row["estimated_delivery"] == "14:30:00"
