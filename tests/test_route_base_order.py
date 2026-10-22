"""Pedido base por cliente de ruta (client_route_item)."""

from sqlalchemy import func, select

from app.models.coreModule.client_route_item import ClientRouteItem
from tests.helpers import API

EVERY_DAY = [1, 2, 3, 4, 5, 6, 7]


def _route_with_client(client, data) -> dict:
    route = client.post(
        f"{API}/routes/",
        json={"name": "ruta base", "days_week": EVERY_DAY, "departure_time": "06:30"},
    ).json()
    assigned = client.post(
        f"{API}/routes/{route['id_route']}/clients",
        json={"id_client": data.client.id_client},
    )
    assert assigned.status_code == 201, assigned.text
    assert assigned.json()["base_items"] == []
    return route


def _put_base(client, id_route, id_client, items):
    return client.put(
        f"{API}/routes/{id_route}/clients/{id_client}/base-order",
        json={"items": items},
    )


def _base(product, cant) -> dict:
    return {"id_product": product.id_product, "cant": cant}


def test_guardar_y_reemplazar_el_pedido_base(client, data):
    route = _route_with_client(client, data)
    p1, p2, p3 = data.products

    saved = _put_base(
        client, route["id_route"], data.client.id_client, [_base(p2, 3), _base(p1, 1)]
    )
    assert saved.status_code == 200, saved.text
    # Respeta el orden en que se enviaron y trae código y nombre del producto
    assert [(i["product_code"], i["cant"]) for i in saved.json()["base_items"]] == [
        ("Z92", 3),
        ("Z91", 1),
    ]

    replaced = _put_base(
        client, route["id_route"], data.client.id_client, [_base(p3, 2)]
    )
    assert [(i["id_product"], i["cant"]) for i in replaced.json()["base_items"]] == [
        (p3.id_product, 2)
    ]

    listed = client.get(f"{API}/routes/{route['id_route']}/clients").json()
    assert [i["product_name"] for i in listed[0]["base_items"]] == ["BOTELLON AGUA"]


def test_lista_vacia_borra_el_pedido_base(client, data):
    route = _route_with_client(client, data)
    _put_base(
        client, route["id_route"], data.client.id_client, [_base(data.products[0], 1)]
    )

    cleared = _put_base(client, route["id_route"], data.client.id_client, [])

    assert cleared.status_code == 200
    assert cleared.json()["base_items"] == []


def test_producto_repetido_se_rechaza(client, data):
    route = _route_with_client(client, data)
    p1 = data.products[0]

    response = _put_base(
        client, route["id_route"], data.client.id_client, [_base(p1, 1), _base(p1, 2)]
    )

    assert response.status_code == 422
    assert response.json()["code"] == "DUPLICATE_PRODUCT"


def test_producto_inactivo_se_rechaza(client, db, data):
    route = _route_with_client(client, data)
    inactive = data.products[2]
    inactive.active = False
    db.commit()

    response = _put_base(
        client, route["id_route"], data.client.id_client, [_base(inactive, 1)]
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REFERENCE_INACTIVE"


def test_cantidad_en_cero_se_rechaza_en_el_schema(client, data):
    route = _route_with_client(client, data)

    response = _put_base(
        client, route["id_route"], data.client.id_client, [_base(data.products[0], 0)]
    )

    assert response.status_code == 422


def test_cliente_que_no_esta_en_la_ruta(client, data):
    route = client.post(
        f"{API}/routes/",
        json={"name": "ruta vacia", "days_week": [1], "departure_time": "06:30"},
    ).json()

    response = _put_base(
        client, route["id_route"], data.client.id_client, [_base(data.products[0], 1)]
    )

    assert response.status_code == 404


def test_quitar_el_cliente_borra_su_pedido_base(client, db, data):
    route = _route_with_client(client, data)
    _put_base(
        client, route["id_route"], data.client.id_client, [_base(data.products[0], 1)]
    )

    removed = client.delete(
        f"{API}/routes/{route['id_route']}/clients/{data.client.id_client}"
    )

    assert removed.status_code == 204
    assert db.scalar(select(func.count()).select_from(ClientRouteItem)) == 0


def test_la_plantilla_precarga_el_pedido_base(client, db, data):
    route = _route_with_client(client, data)
    p1, p2, _ = data.products
    _put_base(
        client, route["id_route"], data.client.id_client, [_base(p2, 4), _base(p1, 1)]
    )
    # Un producto que se desactiva después no se precarga (no se podría pedir)
    p1.active = False
    db.commit()

    template = client.get(f"{API}/orders/routes/{route['id_route']}/template").json()

    [entry] = [c for c in template["clients"] if c["id_client"] == data.client.id_client]
    assert entry["base_items"] == [{"id_product": p2.id_product, "cant": 4}]
