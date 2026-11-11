"""Cambios finales B2: método de pago, tipo de factura y observación del pedido."""

import pytest
from sqlalchemy import func, select

from app.models.coreModule.client import Client
from app.models.coreModule.order import Order
from tests.helpers import API, item


def _new_client_order(client, data, **extra):
    return client.post(
        f"{API}/orders/new-client",
        json={
            "client": {
                "name": "cliente de paso",
                "id_neighborhood": data.neighborhood.id_neighborhood,
            },
            "items": [item(data.products[0], 1)],
            **extra,
        },
    )


def _client_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Client))


# --- Creación ---------------------------------------------------------------------------


def test_por_defecto_efectivo_pos_y_lleva_cd(create_order):
    order = create_order()

    assert order["payment_method"] == "CASH"
    assert order["invoice_type"] == "POS"
    assert order["has_receipt"] is True
    assert order["observations"] is None


def test_crear_con_metodo_de_pago_y_observacion(create_order):
    order = create_order(payment_method="TRANSFER", observations="  Llamar antes  ")

    assert order["payment_method"] == "TRANSFER"
    assert order["has_receipt"] is False  # solo POS + efectivo lleva CD
    assert order["observations"] == "Llamar antes"


@pytest.mark.parametrize("observations", ["", "   "])
def test_observacion_vacia_se_envia_como_null(client, data, observations):
    response = client.post(
        f"{API}/orders/existing-client",
        json={
            "id_client": data.client.id_client,
            "items": [item(data.products[0], 1)],
            "observations": observations,
        },
    )

    assert response.status_code == 422


def test_metodo_de_pago_invalido(client, data):
    response = client.post(
        f"{API}/orders/existing-client",
        json={
            "id_client": data.client.id_client,
            "items": [item(data.products[0], 1)],
            "payment_method": "BITCOIN",
        },
    )

    assert response.status_code == 422


def test_cliente_con_factura_electronica_la_hereda_y_se_puede_cambiar(
    create_order, db, data
):
    data.client.requires_electronic_invoice = True
    db.commit()

    inherited = create_order()
    overridden = create_order(invoice_type="POS")

    assert inherited["invoice_type"] == "ELECTRONIC"
    assert inherited["has_receipt"] is False
    assert overridden["invoice_type"] == "POS"


def test_cambiar_la_marca_del_cliente_no_altera_pedidos_tomados(create_order, db, data):
    order = create_order()
    data.client.requires_electronic_invoice = True
    db.commit()

    db.expire_all()
    assert db.get(Order, order["id_order"]).invoice_type.value == "POS"


def test_cliente_nuevo_factura_pos_con_su_metodo_de_pago(client, data):
    response = _new_client_order(client, data, payment_method="CREDIT")

    assert response.status_code == 201, response.text
    assert response.json()["invoice_type"] == "POS"
    assert response.json()["payment_method"] == "CREDIT"


def test_cliente_nuevo_no_admite_factura_electronica(client, data, db):
    before = _client_count(db)

    response = _new_client_order(client, data, invoice_type="ELECTRONIC")

    assert response.status_code == 422
    assert response.json()["code"] == "ELECTRONIC_INVOICE_NOT_ALLOWED"
    assert _client_count(db) == before  # no quedó el cliente temporal


# --- Edición (PATCH) --------------------------------------------------------------------


def _patch(client, order, **body):
    return client.patch(f"{API}/orders/{order['id_order']}", json=body)


def test_editar_pago_factura_y_observacion_en_pendiente(client, create_order):
    order = create_order()

    response = _patch(
        client,
        order,
        payment_method="CREDIT",
        invoice_type="ELECTRONIC",
        observations="Entregar en portería",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["payment_method"], body["invoice_type"]) == ("CREDIT", "ELECTRONIC")
    assert body["observations"] == "Entregar en portería"
    assert body["has_receipt"] is False


def test_el_pago_se_puede_cambiar_despues_de_despachar(client, create_order):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")

    response = _patch(client, order, payment_method="TRANSFER")

    assert response.status_code == 200, response.text
    assert response.json()["payment_method"] == "TRANSFER"


def test_un_pedido_entregado_no_cambia_el_pago(client, create_order):
    order = create_order()
    client.post(f"{API}/orders/{order['id_order']}/dispatch")
    client.post(f"{API}/orders/{order['id_order']}/deliver")

    response = _patch(client, order, payment_method="TRANSFER")

    assert response.status_code == 422
    assert response.json()["field"] == "payment_method"


@pytest.mark.parametrize("field", ["payment_method", "invoice_type"])
def test_pago_y_factura_no_se_pueden_quitar(client, create_order, field):
    response = _patch(client, create_order(), **{field: None})

    assert response.status_code == 422
    assert response.json()["code"] == "REQUIRED_FIELD"
    assert response.json()["field"] == field


def test_observacion_null_la_borra(client, create_order):
    order = create_order(observations="Algo")

    response = _patch(client, order, observations=None)

    assert response.status_code == 200, response.text
    assert response.json()["observations"] is None


def test_pedido_de_cliente_temporal_no_pasa_a_factura_electronica(client, data):
    order = _new_client_order(client, data).json()

    response = _patch(client, order, invoice_type="ELECTRONIC")

    assert response.status_code == 422
    assert response.json()["code"] == "ELECTRONIC_INVOICE_NOT_ALLOWED"
