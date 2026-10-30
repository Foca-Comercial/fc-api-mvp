"""Pedido pendiente con un producto que se desactivó después de tomarlo: el renglón
se conserva y el pedido se sigue pudiendo editar; lo que no se puede es agregar (o
cambiar un renglón a) un producto inactivo."""

from tests.helpers import API, item


def _sync(client, order, items):
    return client.put(
        f"{API}/orders/{order['id_order']}/items-order", json={"items": items}
    )


def _detail(order, product):
    return next(
        d["id_order_detail"]
        for d in order["order_details"]
        if d["id_product"] == product.id_product
    )


def test_se_edita_el_pedido_con_un_producto_que_se_desactivo(
    client, db, data, create_order
):
    p0, p1, p2 = data.products
    order = create_order(items=[item(p0, 2), item(p1, 1)])
    p0.active = False
    db.commit()

    # Cambia la cantidad del producto inactivo y agrega uno activo
    response = _sync(
        client,
        order,
        [
            {**item(p0, 3), "id_order_detail": _detail(order, p0)},
            {**item(p1, 1), "id_order_detail": _detail(order, p1)},
            {**item(p2, 1), "id_order_detail": None},
        ],
    )

    assert response.status_code == 200, response.text
    details = response.json()["order_details"]
    quantities = {d["id_product"]: d["cant"] for d in details}
    assert quantities == {p0.id_product: 3, p1.id_product: 1, p2.id_product: 1}


def test_se_puede_quitar_el_producto_inactivo(client, db, data, create_order):
    p0, p1, _ = data.products
    order = create_order(items=[item(p0, 2), item(p1, 1)])
    p0.active = False
    db.commit()

    keep = {**item(p1, 1), "id_order_detail": _detail(order, p1)}

    response = _sync(client, order, [keep])

    assert response.status_code == 200, response.text
    assert [d["id_product"] for d in response.json()["order_details"]] == [
        p1.id_product
    ]


def test_no_se_agrega_un_producto_inactivo(client, db, data, create_order):
    p0, p1, p2 = data.products  # noqa: RUF059
    order = create_order(items=[item(p0, 2)])
    p2.active = False
    db.commit()

    response = _sync(
        client,
        order,
        [
            {**item(p0, 2), "id_order_detail": _detail(order, p0)},
            {**item(p2, 1), "id_order_detail": None},
        ],
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REFERENCE_INACTIVE"


def test_un_renglon_no_cambia_a_un_producto_inactivo(client, db, data, create_order):
    p0, _, p2 = data.products
    order = create_order(items=[item(p0, 2)])
    p2.active = False
    db.commit()

    # Mismo renglón, pero con otro producto (inactivo)
    response = _sync(
        client, order, [{**item(p2, 1), "id_order_detail": _detail(order, p0)}]
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REFERENCE_INACTIVE"


def test_el_detalle_indica_si_el_producto_esta_inactivo(client, db, data, create_order):
    p0, p1, _ = data.products
    order = create_order(items=[item(p0, 2), item(p1, 1)])
    p0.active = False
    db.commit()

    detail = client.get(f"{API}/orders/{order['id_order']}/details").json()

    active = {i["id_product"]: i["product_active"] for i in detail["items"]}
    assert active == {p0.id_product: False, p1.id_product: True}
