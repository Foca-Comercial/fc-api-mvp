"""Registro de pedidos: cliente nuevo / existente, cálculo de totales y validaciones."""

from decimal import Decimal

from sqlalchemy import func, select

from app.models.coreModule.client import Client
from app.models.coreModule.order import Order
from tests.helpers import API, item


def _order_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Order))


def test_crear_pedido_cliente_existente_calcula_subtotales_y_total(client, data):
    body = {
        "id_client": data.client.id_client,
        "items": [
            item(data.products[0], 2),  # 2 x 3000
            item(data.products[1], 1, "5500.00"),  # precio editado por el vendedor
        ],
    }
    response = client.post(f"{API}/orders/existing-client", json=body)

    assert response.status_code == 201, response.text
    order = response.json()
    assert order["state"] == "PENDING"
    assert order["id_client"] == data.client.id_client
    assert order["id_user_taker"] == data.taker.id_user  # sale del usuario autenticado
    assert Decimal(order["order_total"]) == Decimal("11500.00")
    subtotals = sorted(Decimal(d["subtotal"]) for d in order["order_details"])
    assert subtotals == [Decimal("5500.00"), Decimal("6000.00")]


def test_crear_pedido_cliente_nuevo_normaliza_nombre_y_direccion(client, data, db):
    """Regresión bug 5: NewClientInput usa UpperText, igual que POST /clients."""
    body = {
        "client": {
            "name": "  pedro pérez ",
            "address": " calle 10 # 5-20 ",
            "id_neighborhood": data.neighborhood.id_neighborhood,
        },
        "items": [item(data.products[0], 1)],
    }
    response = client.post(f"{API}/orders/new-client", json=body)

    assert response.status_code == 201, response.text
    new_client = db.get(Client, response.json()["id_client"])
    assert new_client.name == "PEDRO PÉREZ"
    assert new_client.address == "CALLE 10 # 5-20"
    assert new_client.is_registered is False


def test_crear_pedido_con_producto_repetido_responde_422(client, data, db):
    """Paso 5: un producto no puede aparecer en dos renglones."""
    before = _order_count(db)
    body = {
        "id_client": data.client.id_client,
        "items": [item(data.products[0], 1), item(data.products[0], 3)],
    }
    response = client.post(f"{API}/orders/existing-client", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "DUPLICATE_PRODUCT"
    assert _order_count(db) == before  # no se creó nada


def test_crear_pedido_con_producto_inexistente_no_crea_nada(client, data, db):
    before = _order_count(db)
    body = {
        "id_client": data.client.id_client,
        "items": [{"id_product": 999_999, "cant": 1, "unit_price": "100"}],
    }
    response = client.post(f"{API}/orders/existing-client", json=body)

    assert response.status_code == 422
    assert response.json()["field"] == "id_product"
    assert _order_count(db) == before


def test_busqueda_de_clientes_solo_devuelve_registrados(client, data, db):
    """Formulario de cliente registrado: los temporales no aparecen (opción B)."""
    temporary = Client(
        name="CLIENTE REGISTRADO DE PASO",  # coincide con la búsqueda
        id_neighborhood=data.neighborhood.id_neighborhood,
        is_registered=False,
    )
    db.add(temporary)
    db.commit()

    response = client.get(f"{API}/clients/search?name=registrado")

    assert response.status_code == 200, response.text
    ids = {c["id_client"] for c in response.json()}
    assert data.client.id_client in ids  # "CLIENTE REGISTRADO" (fixture)
    assert temporary.id_client not in ids


def test_pedido_de_cliente_existente_rechaza_temporales(client, data, db):
    """El flujo de cliente registrado no acepta clientes temporales aunque se
    envíe su id_client a mano."""
    temporary = Client(
        name="CLIENTE DE PASO",
        id_neighborhood=data.neighborhood.id_neighborhood,
        is_registered=False,
    )
    db.add(temporary)
    db.commit()
    before = _order_count(db)

    response = client.post(
        f"{API}/orders/existing-client",
        json={"id_client": temporary.id_client, "items": [item(data.products[0], 1)]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CLIENT_NOT_REGISTERED"
    assert _order_count(db) == before
