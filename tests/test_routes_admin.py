"""Panel de administración: rutas (/routes/admin) y lo que el panel necesita de sus
clientes (conteo de precios especiales)."""

from datetime import time
from decimal import Decimal

import pytest

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.models.parametersModule.route import Route
from tests.helpers import API

URL = f"{API}/routes/admin"


@pytest.fixture()
def routes(db):
    """Tres rutas de prueba: norte (lun, jue), sur (mié) y vieja (lun, inactiva)."""
    north = Route(name="TEST NORTE", days_week=[1, 4], departure_time=time(6, 30))
    south = Route(name="TEST SUR", days_week=[3], departure_time=time(7, 0))
    old = Route(
        name="TEST VIEJA", days_week=[1], departure_time=time(5, 0), active=False
    )
    db.add_all([north, south, old])
    db.commit()
    return north, south, old


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [row["name"] for row in response.json()["items"]]


# --- Listado ----------------------------------------------------------------------


def test_lista_por_nombre_con_dias_hora_y_clientes_activos(admin, db, data, routes):
    north = routes[0]
    inactive = Client(
        name="INACTIVO", id_neighborhood=data.neighborhood.id_neighborhood, active=False
    )
    db.add(inactive)
    db.flush()
    db.add_all(
        ClientRoute(id_route=north.id_route, id_client=c.id_client)
        for c in (data.client, inactive)
    )
    db.commit()

    response = admin.get(URL, params={"search": "test"})

    assert _names(response) == ["TEST NORTE", "TEST SUR", "TEST VIEJA"]
    row = response.json()["items"][0]
    assert row["days_week"] == [1, 4]
    assert row["departure_time"] == "06:30:00"
    assert row["clients_count"] == 1  # el inactivo no cuenta


def test_filtra_por_estado_y_dia(admin, routes):
    def names(**params):
        return _names(admin.get(URL, params={"search": "test", **params}))

    assert names(active="false") == ["TEST VIEJA"]
    assert names(day=1) == ["TEST NORTE", "TEST VIEJA"]
    assert names(day=1, active="true") == ["TEST NORTE"]
    assert names(day=3) == ["TEST SUR"]
    assert names(day=7) == []


@pytest.mark.parametrize("day", [0, 8])
def test_dia_invalido(admin, day):
    assert admin.get(URL, params={"day": day}).status_code == 422


# --- Editar -----------------------------------------------------------------------


def test_no_se_vacian_campos_obligatorios(admin, routes):
    url = f"{API}/routes/{routes[0].id_route}"

    for field in ("name", "days_week", "departure_time"):
        response = admin.patch(url, json={field: None})
        assert response.status_code == 422, field
        assert response.json()["code"] == "REQUIRED_FIELD"
        assert response.json()["field"] == field


def test_nombre_unico(admin, routes):
    response = admin.patch(
        f"{API}/routes/{routes[1].id_route}", json={"name": "test norte"}
    )

    assert response.status_code == 409


def test_desactivar_la_saca_de_las_rutas_del_dia(admin, routes):
    north = routes[0]
    monday = "2026-11-02"

    before = admin.get(f"{API}/orders/routes-of-day", params={"target_date": monday})
    admin.patch(f"{API}/routes/{north.id_route}", json={"active": False})
    after = admin.get(f"{API}/orders/routes-of-day", params={"target_date": monday})

    assert north.id_route in {r["id_route"] for r in before.json()}
    assert north.id_route not in {r["id_route"] for r in after.json()}


# --- Clientes de la ruta: precios especiales --------------------------------------


def test_clientes_de_la_ruta_traen_sus_precios_especiales(admin, db, data, routes):
    north = routes[0]
    active_product, inactive_product = data.products[0], data.products[1]
    inactive_product.active = False
    db.add(ClientRoute(id_route=north.id_route, id_client=data.client.id_client))
    db.add_all(
        SpecialCustomerPrice(
            id_client=data.client.id_client,
            id_product=p.id_product,
            agreed_price=Decimal("1000"),
        )
        for p in (active_product, inactive_product)
    )
    db.commit()

    clients = admin.get(f"{API}/routes/{north.id_route}/clients").json()

    # Solo cuentan los productos activos: son los que se piden desde la ruta
    assert clients[0]["special_prices_count"] == 1


def test_el_selector_trae_los_precios_especiales(admin, db, data, routes):
    other = Client(
        name="SIN PRECIOS",
        id_neighborhood=data.neighborhood.id_neighborhood,
        is_registered=True,
    )
    db.add(other)
    db.add(
        SpecialCustomerPrice(
            id_client=data.client.id_client,
            id_product=data.products[0].id_product,
            agreed_price=Decimal("1000"),
        )
    )
    db.commit()

    available = admin.get(f"{API}/routes/{routes[1].id_route}/available-clients")

    counts = {c["id_client"]: c["special_prices_count"] for c in available.json()}
    assert counts[data.client.id_client] == 1
    assert counts[other.id_client] == 0


# --- Roles ------------------------------------------------------------------------


def test_el_gestor_no_accede_al_panel_de_rutas(client):
    assert client.get(URL).status_code == 403
