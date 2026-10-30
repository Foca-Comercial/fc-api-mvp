"""Panel de administración: gestión de productos (/products/admin)."""

from decimal import Decimal

import pytest

from app.models.coreModule.product import Product
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from tests.helpers import API, item

URL = f"{API}/products/admin"
TEST_SEARCH = {"search": "Z9"}  # productos del fixture `data` (Z91, Z92, Z93)


def _codes(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [row["code"] for row in response.json()["items"]]


def _new(api, code="901", name="hielo en cubos", price="4500", **extra):
    return api.post(
        URL, json={"code": code, "name": name, "base_price": price, **extra}
    )


# --- Listado ----------------------------------------------------------------------


def test_lista_por_codigo_con_conteos_y_uso(admin, db, data, create_order):
    create_order()  # usa el primer producto (Z91)
    db.add(
        SpecialCustomerPrice(
            id_client=data.client.id_client,
            id_product=data.products[1].id_product,
            agreed_price=Decimal("5500"),
        )
    )
    db.commit()

    response = admin.get(URL, params=TEST_SEARCH)

    rows = {row["code"]: row for row in response.json()["items"]}
    assert _codes(response) == ["Z91", "Z92", "Z93"]
    assert rows["Z91"]["in_use"] is True
    assert rows["Z92"]["in_use"] is False
    assert rows["Z92"]["special_prices_count"] == 1
    assert rows["Z93"]["base_price"] == "8000.00"


def test_busca_por_inicio_del_codigo_o_por_nombre(admin, data):
    assert _codes(admin.get(URL, params={"search": "Z92"})) == ["Z92"]
    assert _codes(admin.get(URL, params={"search": "botellon"})) == ["Z93"]
    # El código se busca por el inicio
    assert _codes(admin.get(URL, params={"search": "92"})) == []


def test_filtra_por_estado(admin, db, data):
    data.products[2].active = False
    db.commit()

    active = _codes(admin.get(URL, params={**TEST_SEARCH, "active": "true"}))
    inactive = _codes(admin.get(URL, params={**TEST_SEARCH, "active": "false"}))

    assert active == ["Z91", "Z92"]
    assert inactive == ["Z93"]


# --- Crear ------------------------------------------------------------------------


def test_crea_un_producto(admin):
    response = _new(admin, description="bolsa de 2 kg")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "901"
    assert body["name"] == "HIELO EN CUBOS"
    assert body["description"] == "BOLSA DE 2 KG"
    assert body["base_price"] == "4500.00"
    assert (body["active"], body["in_use"], body["special_prices_count"]) == (
        True,
        False,
        0,
    )


def test_no_se_repite_el_codigo(admin):
    _new(admin)

    response = _new(admin, name="otro")

    assert response.status_code == 409
    assert response.json()["field"] == "code"


@pytest.mark.parametrize(
    "body",
    [
        {"code": "AB1"},
        {"code": "12"},
        {"base_price": "-1"},
        {"base_price": "10.555"},
        {"name": "   "},
    ],
)
def test_crear_valida_los_campos(admin, body):
    payload = {"code": "902", "name": "HIELO", "base_price": "1000", **body}

    assert admin.post(URL, json=payload).status_code == 422


# --- Editar, desactivar y reactivar ---------------------------------------------


def test_edicion_parcial(admin, data):
    product = data.products[1]

    response = admin.patch(
        f"{URL}/{product.id_product}",
        json={"base_price": "6500", "name": "bolsa 5 kg"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["base_price"] == "6500.00"
    assert response.json()["name"] == "BOLSA 5 KG"
    assert response.json()["code"] == "Z92"  # lo no enviado no cambia


def test_cambia_el_codigo_si_no_tiene_pedidos(admin, data):
    product = data.products[1]

    response = admin.patch(f"{URL}/{product.id_product}", json={"code": "992"})

    assert response.status_code == 200, response.text
    assert response.json()["code"] == "992"


def test_no_cambia_el_codigo_si_tiene_pedidos(admin, db, data, create_order):
    product = Product(code="904", name="HIELO TEST", base_price=Decimal("3000"))
    db.add(product)
    db.commit()
    create_order(items=[item(product, 1)])
    url = f"{URL}/{product.id_product}"

    blocked = admin.patch(url, json={"code": "905"})
    # Reenviar el mismo código (p. ej. el formulario completo) sí se permite
    same_code = admin.patch(url, json={"code": "904", "base_price": "3100"})

    assert blocked.status_code == 422
    assert blocked.json()["code"] == "PRODUCT_CODE_IN_USE"
    assert same_code.status_code == 200, same_code.text


def test_no_cambia_a_un_codigo_de_otro_producto(admin, db, data):
    other = Product(code="903", name="OTRO", base_price=Decimal("1"))
    db.add(other)
    db.commit()

    response = admin.patch(
        f"{URL}/{data.products[1].id_product}", json={"code": "903"}
    )

    assert response.status_code == 409


def test_no_se_vacian_campos_obligatorios(admin, data):
    response = admin.patch(
        f"{URL}/{data.products[0].id_product}", json={"base_price": None}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REQUIRED_FIELD"
    assert response.json()["field"] == "base_price"


def test_desactivado_sale_del_catalogo_y_se_reactiva(admin, data):
    product = data.products[2]
    url = f"{URL}/{product.id_product}"

    off = admin.patch(url, json={"active": False})
    catalog = {p["id_product"] for p in admin.get(f"{API}/products/catalog").json()}
    on = admin.patch(url, json={"active": True})

    assert off.json()["active"] is False
    assert product.id_product not in catalog
    assert on.json()["active"] is True


def test_editar_producto_inexistente(admin):
    assert admin.patch(f"{URL}/999999", json={"active": False}).status_code == 404


# --- Roles ------------------------------------------------------------------------


def test_el_gestor_no_accede_al_panel_de_productos(client, data):
    assert client.get(URL).status_code == 403
    assert _new(client).status_code == 403
    url = f"{URL}/{data.products[0].id_product}"
    assert client.patch(url, json={"active": False}).status_code == 403
