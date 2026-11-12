"""Cambios finales B4: detalle del pedido con auditoría.

Fecha y hora de creación (Bogotá), quién registró el pedido, quién editó los
productos por última vez y cuándo, facturación, ruta y datos de la cancelación.
"""

import re
from datetime import UTC, date, datetime, time, timedelta

from app.core.timezone import today_bogota
from app.models.coreModule.order import Order
from app.models.parametersModule.route import Route
from app.utils.enums.cancel_reason import CancelReason
from tests.helpers import API, item, mark_cancelled


def _detail(client, order: dict) -> dict:
    response = client.get(f"{API}/orders/{order['id_order']}/details")
    assert response.status_code == 200, response.text
    return response.json()


def _sync(client, order: dict, items: list[dict]):
    return client.put(
        f"{API}/orders/{order['id_order']}/items-order", json={"items": items}
    )


def _current_items(client, order: dict) -> list[dict]:
    """La lista actual del pedido tal como se envía al editar."""
    return [
        {
            "id_order_detail": i["id_order_detail"],
            "id_product": i["id_product"],
            "cant": i["cant"],
            "unit_price": i["unit_price"],
        }
        for i in _detail(client, order)["items"]
    ]


# --- Datos nuevos del detalle -------------------------------------------------------------


def test_detalle_trae_creacion_quien_registro_y_facturacion(client, create_order):
    order = create_order(observations="Tocar el timbre")

    detail = _detail(client, order)

    assert detail["creation_date"] == today_bogota().isoformat()
    assert re.fullmatch(r"\d{2}:\d{2}", detail["creation_time"])
    assert detail["creation_datetime"].endswith("-05:00")  # hora de Bogotá
    assert detail["taker_name"] == "Ana Gestora"
    assert detail["items_updater_name"] is None
    assert detail["items_updated_at"] is None
    assert (detail["payment_method"], detail["invoice_type"]) == ("CASH", "POS")
    assert detail["has_receipt"] is True
    assert detail["observations"] == "Tocar el timbre"
    assert (detail["id_route"], detail["route_name"]) == (None, None)
    assert detail["cancel_reason"] is None
    assert detail["canceller_name"] is None


def test_fecha_y_hora_de_creacion_en_bogota(client, create_order, db):
    order = create_order()
    # 03:00 UTC del 10 de octubre = 22:00 del 9 de octubre en Bogotá
    db.get(Order, order["id_order"]).creation_datetime = datetime(
        2026, 10, 10, 3, 0, tzinfo=UTC
    )
    db.commit()

    detail = _detail(client, order)

    assert detail["creation_date"] == date(2026, 10, 9).isoformat()
    assert detail["creation_time"] == "22:00"


def test_detalle_de_pedido_programado_distingue_creacion_y_entrega(
    client, create_order
):
    scheduled_for = today_bogota() + timedelta(days=3)
    order = create_order(delivery_date=scheduled_for.isoformat())

    detail = _detail(client, order)

    assert detail["creation_date"] == today_bogota().isoformat()
    assert detail["delivery_date"] == scheduled_for.isoformat()


def test_detalle_trae_la_ruta(client, create_order, db):
    route = Route(name="RUTA DETALLE", days_week=[1], departure_time=time(6, 0))
    db.add(route)
    db.commit()
    order = create_order()
    db.get(Order, order["id_order"]).id_route = route.id_route
    db.commit()

    detail = _detail(client, order)

    assert (detail["id_route"], detail["route_name"]) == (route.id_route, "RUTA DETALLE")


def test_detalle_de_pedido_cancelado(client, create_order, db, data):
    order = create_order()
    cancelled = mark_cancelled(db, order["id_order"])
    cancelled.cancel_reason = CancelReason.CLIENT_ABSENT
    cancelled.cancel_note = "No abrieron"
    cancelled.cancelled_at = datetime(2026, 10, 10, 15, 30, tzinfo=UTC)
    cancelled.id_user_canceller = data.taker.id_user
    db.commit()

    detail = _detail(client, order)

    assert detail["state"] == "CANCELLED"
    assert detail["cancel_reason"] == "CLIENT_ABSENT"
    assert detail["cancel_note"] == "No abrieron"
    assert detail["cancelled_at"].startswith("2026-10-10T10:30:00")  # Bogotá
    assert detail["canceller_name"] == "Ana Gestora"


# --- Auditoría de la edición de productos -------------------------------------------------


def test_editar_productos_registra_quien_y_cuando(client, create_order, data):
    order = create_order()
    items = _current_items(client, order)
    items[0]["cant"] = 5

    response = _sync(client, order, items)

    assert response.status_code == 200, response.text
    assert response.json()["items_updated_at"] is not None
    detail = _detail(client, order)
    assert detail["items_updater_name"] == "Ana Gestora"
    assert detail["items_updated_at"] is not None


def test_agregar_un_producto_cuenta_como_edicion(client, create_order, data):
    order = create_order()
    items = _current_items(client, order) + [item(data.products[1], 1)]

    _sync(client, order, items)

    assert _detail(client, order)["items_updater_name"] == "Ana Gestora"


def test_reenviar_la_misma_lista_no_cuenta_como_edicion(client, create_order):
    order = create_order()

    response = _sync(client, order, _current_items(client, order))

    assert response.status_code == 200, response.text
    detail = _detail(client, order)
    assert detail["items_updater_name"] is None
    assert detail["items_updated_at"] is None


def test_patch_del_pedido_no_cuenta_como_edicion_de_productos(client, create_order):
    order = create_order()

    client.patch(
        f"{API}/orders/{order['id_order']}",
        json={"payment_method": "TRANSFER", "observations": "Pagará al recibir"},
    )

    detail = _detail(client, order)
    assert detail["payment_method"] == "TRANSFER"
    assert detail["items_updater_name"] is None
