"""Panel de administración: precios especiales de un cliente registrado
(/clients/admin/{id}/special-prices)."""

from datetime import time

import pytest
from sqlalchemy import func, select

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.models.parametersModule.route import Route
from tests.helpers import API


def _url(id_client: int, id_product: int | None = None) -> str:
    base = f"{API}/clients/admin/{id_client}/special-prices"
    return base if id_product is None else f"{base}/{id_product}"


def _set(api, id_client, id_product, price="2500.00"):
    return api.put(_url(id_client, id_product), json={"agreed_price": price})


def test_asigna_y_lista_por_codigo(admin, data):
    z91, _, z93 = data.products
    first = _set(admin, data.client.id_client, z93.id_product, "7500")
    _set(admin, data.client.id_client, z91.id_product, "2500.50")

    assert first.status_code == 200, first.text
    assert first.json() == {
        "id_product": z93.id_product,
        "product_code": "Z93",
        "product_name": "BOTELLON AGUA",
        "product_active": True,
        "base_price": "8000.00",
        "agreed_price": "7500.00",
    }
    listed = admin.get(_url(data.client.id_client)).json()
    assert [row["product_code"] for row in listed] == ["Z91", "Z93"]
    assert listed[0]["agreed_price"] == "2500.50"


def test_sin_precios_la_lista_esta_vacia(admin, data):
    response = admin.get(_url(data.client.id_client))

    assert response.status_code == 200
    assert response.json() == []


def test_poner_de_nuevo_el_precio_lo_actualiza(admin, db, data):
    product = data.products[0]
    _set(admin, data.client.id_client, product.id_product, "2500")

    response = _set(admin, data.client.id_client, product.id_product, "2400")

    assert response.status_code == 200, response.text
    assert response.json()["agreed_price"] == "2400.00"
    count = db.scalar(
        select(func.count())
        .select_from(SpecialCustomerPrice)
        .where(SpecialCustomerPrice.id_client == data.client.id_client)
    )
    assert count == 1


@pytest.mark.parametrize("price", ["-1", "10.555", "abc"])
def test_precio_invalido(admin, data, price):
    response = _set(admin, data.client.id_client, data.products[0].id_product, price)

    assert response.status_code == 422


def test_producto_inexistente(admin, data):
    response = _set(admin, data.client.id_client, 999999)

    assert response.status_code == 422
    assert response.json()["field"] == "id_product"


def test_no_se_asigna_un_producto_inactivo_pero_si_se_edita_uno_existente(
    admin, db, data
):
    new_one, priced = data.products[0], data.products[1]
    _set(admin, data.client.id_client, priced.id_product, "5000")
    new_one.active = False
    priced.active = False
    db.commit()

    rejected = _set(admin, data.client.id_client, new_one.id_product)
    edited = _set(admin, data.client.id_client, priced.id_product, "4800")

    assert rejected.status_code == 422
    assert rejected.json()["code"] == "REFERENCE_INACTIVE"
    assert edited.status_code == 200, edited.text
    assert edited.json()["product_active"] is False


def test_quitar_un_precio(admin, data):
    product = data.products[0]
    _set(admin, data.client.id_client, product.id_product)

    removed = admin.delete(_url(data.client.id_client, product.id_product))
    again = admin.delete(_url(data.client.id_client, product.id_product))

    assert removed.status_code == 204
    assert admin.get(_url(data.client.id_client)).json() == []
    assert again.status_code == 404


def test_el_conteo_del_listado_de_clientes_refleja_los_precios(admin, data):
    for product in data.products[:2]:
        _set(admin, data.client.id_client, product.id_product)

    page = admin.get(
        f"{API}/clients/admin", params={"search": "CLIENTE REGISTRADO"}
    ).json()

    assert page["items"][0]["special_prices_count"] == 2


def test_la_plantilla_de_ruta_usa_el_precio_pactado(admin, db, data):
    route = Route(name="RUTA PRECIOS", days_week=[1], departure_time=time(6, 0))
    db.add(route)
    db.flush()
    db.add(ClientRoute(id_route=route.id_route, id_client=data.client.id_client))
    db.commit()
    _set(admin, data.client.id_client, data.products[0].id_product, "2750")

    template = admin.get(f"{API}/orders/routes/{route.id_route}/template").json()

    [client] = template["clients"]
    [product] = client["products"]
    assert product["id_product"] == data.products[0].id_product
    assert product["unit_price"] == "2750.00"


# --- Solo clientes registrados -------------------------------------------------


def test_cliente_temporal_o_inexistente(admin, db, data):
    temporary = Client(
        name="CLIENTE DE PASO", id_neighborhood=data.neighborhood.id_neighborhood
    )
    db.add(temporary)
    db.commit()
    product = data.products[0].id_product

    for response in (
        admin.get(_url(temporary.id_client)),
        _set(admin, temporary.id_client, product),
        admin.delete(_url(temporary.id_client, product)),
    ):
        assert response.status_code == 422
        assert response.json()["code"] == "CLIENT_NOT_REGISTERED"

    assert admin.get(_url(999999)).status_code == 404


def test_el_gestor_no_gestiona_precios(client, data):
    product = data.products[0].id_product

    assert client.get(_url(data.client.id_client)).status_code == 403
    assert _set(client, data.client.id_client, product).status_code == 403
    assert client.delete(_url(data.client.id_client, product)).status_code == 403
