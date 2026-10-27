"""Ciclo de vida del pedido: despacho, entrega, reasignación de conductor y
sincronización de productos."""

from decimal import Decimal

from tests.helpers import API, item

# --- Despacho y entrega ---------------------------------------------------------


def test_despachar_pedido_pendiente(client, create_order):
    order = create_order()

    response = client.post(f"{API}/orders/{order['id_order']}/dispatch")

    assert response.status_code == 200, response.text
    assert response.json()["state"] == "DISPATCHED"
    assert response.json()["dispatch_time"] is not None


def test_no_se_despacha_dos_veces(client, create_order):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    response = client.post(f"{API}/orders/{order['id_order']}/dispatch")

    assert response.status_code == 422
    assert response.json()["field"] == "state"


def test_no_se_entrega_un_pedido_sin_despachar(client, create_order):
    order = create_order()

    response = client.post(f"{API}/orders/{order['id_order']}/deliver")

    assert response.status_code == 422


def test_entregar_pedido_despachado(client, create_order):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    response = client.post(f"{API}/orders/{order['id_order']}/deliver")

    assert response.status_code == 200, response.text
    assert response.json()["state"] == "DELIVERED"
    assert response.json()["delivery_time"] is not None


# --- PATCH: reasignar conductor (regresión bug 2) --------------------------------


def test_patch_solo_con_conductor(client, create_order, data):
    order = create_order()

    response = client.patch(
        f"{API}/orders/{order['id_order']}",
        json={"id_user_vehicle": data.user_vehicle.id_user_vehicle},
    )

    assert response.status_code == 200, response.text
    assert response.json()["id_user_vehicle"] == data.user_vehicle.id_user_vehicle


def test_patch_ignora_campos_distintos_al_conductor(client, create_order, data):
    order = create_order()

    response = client.patch(
        f"{API}/orders/{order['id_order']}",
        json={
            "id_user_vehicle": data.user_vehicle.id_user_vehicle,
            "order_total": "1.00",
            "purchase_order": "999",
            "id_client": 999_999,
        },
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    assert Decimal(updated["order_total"]) == Decimal(order["order_total"])
    assert updated["purchase_order"] == order["purchase_order"]
    assert updated["id_client"] == order["id_client"]


def test_patch_con_null_desasigna_conductor(client, create_order, data):
    order = create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle)

    response = client.patch(
        f"{API}/orders/{order['id_order']}", json={"id_user_vehicle": None}
    )

    assert response.status_code == 200, response.text
    assert response.json()["id_user_vehicle"] is None


def test_patch_bloqueado_en_pedido_entregado(client, create_order, data):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")
    client.post(f"{API}/orders/{order['id_order']}/deliver")

    response = client.patch(
        f"{API}/orders/{order['id_order']}",
        json={"id_user_vehicle": data.user_vehicle.id_user_vehicle},
    )

    assert response.status_code == 422


def test_patch_con_conductor_inexistente(client, create_order):
    order = create_order()

    response = client.patch(
        f"{API}/orders/{order['id_order']}", json={"id_user_vehicle": 999_999}
    )

    assert response.status_code == 422
    assert response.json()["field"] == "id_user_vehicle"


def test_patch_cambia_hora_estimada_sin_tocar_el_conductor(client, create_order, data):
    order = create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle)

    response = client.patch(
        f"{API}/orders/{order['id_order']}", json={"estimated_delivery": "15:30:00"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["estimated_delivery"] == "15:30:00"
    assert response.json()["id_user_vehicle"] == data.user_vehicle.id_user_vehicle


def test_patch_solo_conductor_no_toca_la_hora_estimada(client, create_order, data):
    order = create_order(estimated_delivery="10:00:00")

    response = client.patch(
        f"{API}/orders/{order['id_order']}",
        json={"id_user_vehicle": data.user_vehicle.id_user_vehicle},
    )

    assert response.status_code == 200, response.text
    assert response.json()["estimated_delivery"] == "10:00:00"


def test_patch_con_null_quita_la_hora_estimada(client, create_order):
    order = create_order(estimated_delivery="10:00:00")

    response = client.patch(
        f"{API}/orders/{order['id_order']}", json={"estimated_delivery": None}
    )

    assert response.status_code == 200, response.text
    assert response.json()["estimated_delivery"] is None


def test_patch_hora_estimada_bloqueada_en_pedido_despachado(client, create_order):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    response = client.patch(
        f"{API}/orders/{order['id_order']}", json={"estimated_delivery": "15:30:00"}
    )

    assert response.status_code == 422
    assert response.json()["field"] == "estimated_delivery"


def test_patch_conductor_permitido_en_pedido_despachado(client, create_order, data):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    response = client.patch(
        f"{API}/orders/{order['id_order']}",
        json={"id_user_vehicle": data.user_vehicle.id_user_vehicle},
    )

    assert response.status_code == 200, response.text
    assert response.json()["id_user_vehicle"] == data.user_vehicle.id_user_vehicle


# --- PUT /items-order: sincronización de productos -------------------------------


def test_sync_edita_agrega_y_elimina_renglones(client, create_order, data):
    p0, p1, p2 = data.products
    order = create_order(items=[item(p0, 2), item(p1, 1)])
    detail_p0 = next(
        d for d in order["order_details"] if d["id_product"] == p0.id_product
    )

    response = client.put(
        f"{API}/orders/{order['id_order']}/items-order",
        json={
            "items": [
                # edita el renglón existente de p0 (2 -> 5); p1 no viene: se elimina
                {**item(p0, 5), "id_order_detail": detail_p0["id_order_detail"]},
                # renglón nuevo
                {**item(p2, 1, "7500.00"), "id_order_detail": None},
            ]
        },
    )

    assert response.status_code == 200, response.text
    synced = response.json()
    by_product = {d["id_product"]: d for d in synced["order_details"]}
    assert set(by_product) == {p0.id_product, p2.id_product}
    assert by_product[p0.id_product]["id_order_detail"] == detail_p0["id_order_detail"]
    assert by_product[p0.id_product]["cant"] == 5
    assert Decimal(synced["order_total"]) == Decimal("22500.00")  # 5*3000 + 7500


def test_sync_con_producto_repetido_no_modifica_el_pedido(client, create_order, data):
    """Paso 5: la validación ocurre antes de tocar cualquier renglón."""
    p0, p1, _ = data.products
    order = create_order(items=[item(p0, 2), item(p1, 1)])

    response = client.put(
        f"{API}/orders/{order['id_order']}/items-order",
        json={"items": [item(p0, 1), item(p0, 4)]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "DUPLICATE_PRODUCT"
    detail = client.get(f"{API}/orders/{order['id_order']}/details").json()
    assert len(detail["items"]) == 2
    assert Decimal(detail["order_total"]) == Decimal(order["order_total"])


def test_sync_rechaza_detalle_de_otro_pedido(client, create_order, data):
    p0 = data.products[0]
    other = create_order(items=[item(p0, 1)])
    order = create_order(items=[item(p0, 1)])
    foreign_detail = other["order_details"][0]["id_order_detail"]

    response = client.put(
        f"{API}/orders/{order['id_order']}/items-order",
        json={"items": [{**item(p0, 3), "id_order_detail": foreign_detail}]},
    )

    assert response.status_code == 422
    assert response.json()["field"] == "id_order_detail"


def test_sync_solo_en_pedido_pendiente(client, create_order, data):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    response = client.put(
        f"{API}/orders/{order['id_order']}/items-order",
        json={"items": [item(data.products[1], 1)]},
    )

    assert response.status_code == 422


# --- Endpoints retirados -----------------------------------------------------------


def test_no_existe_delete_de_pedidos(client, create_order):
    """Regresión bug 4: un pedido no se elimina, se cancela."""
    order = create_order()

    response = client.delete(f"{API}/orders/{order['id_order']}")

    assert response.status_code == 405


def test_orders_details_es_solo_lectura(client, create_order):
    """Paso 5: los detalles solo se modifican vía PUT /orders/{id}/items-order."""
    order = create_order()
    detail_id = order["order_details"][0]["id_order_detail"]

    assert client.post(f"{API}/orders_details/", json={}).status_code == 405
    assert client.patch(f"{API}/orders_details/{detail_id}", json={}).status_code == 405
    assert client.delete(f"{API}/orders_details/{detail_id}").status_code == 405
