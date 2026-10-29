"""Panel de administración: gestión de clientes registrados (/clients/admin)."""

from datetime import time
from decimal import Decimal

import pytest

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.route import Route
from app.models.parametersModule.zone import Zone
from tests.helpers import API

URL = f"{API}/clients/admin"


def _client(
    db, data, name, *, registered=True, active=True, phone=None, neighborhood=None
):
    new = Client(
        name=name,
        phone=phone,
        id_neighborhood=(neighborhood or data.neighborhood).id_neighborhood,
        is_registered=registered,
        active=active,
    )
    db.add(new)
    db.commit()
    return new


def _ids(response) -> list[int]:
    assert response.status_code == 200, response.text
    return [row["id_client"] for row in response.json()["items"]]


# --- Listado ----------------------------------------------------------------------


def test_lista_solo_registrados_con_barrio_y_zona(admin, db, data):
    temporary = _client(db, data, "CLIENTE DE PASO", registered=False)

    response = admin.get(URL)

    ids = _ids(response)
    assert data.client.id_client in ids
    assert temporary.id_client not in ids
    rows = {r["id_client"]: r for r in response.json()["items"]}
    row = rows[data.client.id_client]
    assert row["neighborhood_name"] == "BARRIO TEST"
    assert row["zone_name"] == "ZONA TEST"
    assert row["special_prices_count"] == 0
    assert row["routes_count"] == 0


def test_conteo_de_precios_especiales_y_rutas(admin, db, data):
    db.add_all(
        SpecialCustomerPrice(
            id_client=data.client.id_client,
            id_product=product.id_product,
            agreed_price=Decimal("2500.00"),
        )
        for product in data.products[:2]
    )
    route = Route(name="RUTA CONTEO", days_week=[1], departure_time=time(6, 0))
    db.add(route)
    db.flush()
    db.add(ClientRoute(id_route=route.id_route, id_client=data.client.id_client))
    db.commit()

    response = admin.get(URL, params={"search": "CLIENTE REGISTRADO"})

    [row] = response.json()["items"]
    assert row["special_prices_count"] == 2
    assert row["routes_count"] == 1


def test_busca_por_nombre_o_inicio_del_telefono(admin, db, data):
    store = _client(db, data, "TIENDA LA ESQUINA", phone="3001112233")
    _client(db, data, "PANADERIA CENTRAL", phone="3109998877")

    assert _ids(admin.get(URL, params={"search": "esquina"})) == [store.id_client]
    assert _ids(admin.get(URL, params={"search": "300111"})) == [store.id_client]
    # El teléfono se busca por el inicio, no por cualquier parte
    assert _ids(admin.get(URL, params={"search": "112233"})) == []


def test_la_busqueda_trata_comodines_como_texto(admin, db, data):
    literal = _client(db, data, "DESCUENTO 50% SAS")
    _client(db, data, "DESCUENTO 500 SAS")

    assert _ids(admin.get(URL, params={"search": "50%"})) == [literal.id_client]


def test_filtra_por_estado_y_zona(admin, db, data):
    zone = Zone(name="ZONA SUR TEST", commune_code="Z98")
    db.add(zone)
    db.flush()
    south = Neighborhood(name="BARRIO SUR", id_zone=zone.id_zone)
    db.add(south)
    db.flush()
    in_south = _client(db, data, "CLIENTE DEL SUR", neighborhood=south)
    inactive = _client(db, data, "CLIENTE INACTIVO", active=False)

    by_zone = admin.get(URL, params={"id_zone": zone.id_zone})
    assert _ids(by_zone) == [in_south.id_client]
    assert _ids(admin.get(URL, params={"active": "false"})) == [inactive.id_client]
    assert inactive.id_client not in _ids(admin.get(URL, params={"active": "true"}))


def test_pagina_ordenado_por_nombre(admin, db, data):
    for name in ("ZZ CLIENTE C", "ZZ CLIENTE A", "ZZ CLIENTE B"):
        _client(db, data, name)

    first = admin.get(URL, params={"search": "ZZ CLIENTE", "page_size": 2}).json()
    second = admin.get(
        URL, params={"search": "ZZ CLIENTE", "page_size": 2, "page": 2}
    ).json()

    assert (first["total"], first["pages"]) == (3, 2)
    assert [r["name"] for r in first["items"]] == ["ZZ CLIENTE A", "ZZ CLIENTE B"]
    assert [r["name"] for r in second["items"]] == ["ZZ CLIENTE C"]


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 201}])
def test_parametros_de_pagina_invalidos(admin, params):
    assert admin.get(URL, params=params).status_code == 422


# --- Crear ------------------------------------------------------------------------


def test_crea_un_cliente_registrado(admin, db, data):
    response = admin.post(
        URL,
        json={
            "name": "  tienda nueva  ",
            "phone": "3001234567",
            "address": "calle 1 # 2-3",
            "id_neighborhood": data.neighborhood.id_neighborhood,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "TIENDA NUEVA"
    assert body["address"] == "CALLE 1 # 2-3"
    assert body["zone_name"] == "ZONA TEST"
    assert body["active"] is True
    assert db.get(Client, body["id_client"]).is_registered is True


@pytest.mark.parametrize("phone", ["123", "30012345678", "300123456a"])
def test_crear_rechaza_telefono_invalido(admin, data, phone):
    response = admin.post(
        URL,
        json={
            "name": "TIENDA",
            "phone": phone,
            "id_neighborhood": data.neighborhood.id_neighborhood,
        },
    )

    assert response.status_code == 422


def test_crear_rechaza_barrio_inactivo_o_inexistente(admin, db, data):
    inactive = Neighborhood(
        name="BARRIO CERRADO", id_zone=data.neighborhood.id_zone, active=False
    )
    db.add(inactive)
    db.commit()

    closed = admin.post(
        URL, json={"name": "TIENDA", "id_neighborhood": inactive.id_neighborhood}
    )
    missing = admin.post(URL, json={"name": "TIENDA", "id_neighborhood": 999999})

    assert closed.status_code == 422
    assert closed.json()["code"] == "REFERENCE_INACTIVE"
    assert missing.status_code == 422
    assert missing.json()["field"] == "id_neighborhood"


# --- Editar, desactivar y reactivar ---------------------------------------------


def test_edicion_parcial(admin, data):
    url = f"{URL}/{data.client.id_client}"

    response = admin.patch(url, json={"phone": "3005556677"})

    assert response.status_code == 200, response.text
    assert response.json()["phone"] == "3005556677"
    assert response.json()["name"] == "CLIENTE REGISTRADO"  # lo no enviado no cambia


def test_desactiva_y_reactiva(admin, db, data):
    url = f"{URL}/{data.client.id_client}"

    off = admin.patch(url, json={"active": False})
    assert off.status_code == 200, off.text
    assert off.json()["active"] is False

    on = admin.patch(url, json={"active": True})
    assert on.json()["active"] is True
    db.expire_all()
    assert db.get(Client, data.client.id_client).active is True


def test_no_se_vacian_campos_obligatorios(admin, data):
    response = admin.patch(f"{URL}/{data.client.id_client}", json={"name": None})

    assert response.status_code == 422
    assert response.json()["code"] == "REQUIRED_FIELD"
    assert response.json()["field"] == "name"


def test_no_se_gestionan_clientes_temporales(admin, db, data):
    temporary = _client(db, data, "CLIENTE DE PASO", registered=False)

    response = admin.patch(
        f"{URL}/{temporary.id_client}", json={"phone": "3001234567"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CLIENT_NOT_REGISTERED"


def test_editar_cliente_inexistente(admin):
    assert admin.patch(f"{URL}/999999", json={"active": False}).status_code == 404


# --- Roles ------------------------------------------------------------------------


def test_el_gestor_no_accede_al_panel_de_clientes(client, data):
    body = {"name": "TIENDA", "id_neighborhood": data.neighborhood.id_neighborhood}

    assert client.get(URL).status_code == 403
    assert client.post(URL, json=body).status_code == 403
    edit = client.patch(f"{URL}/{data.client.id_client}", json=body)
    assert edit.status_code == 403
