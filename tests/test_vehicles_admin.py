"""Panel de administración: gestión de vehículos (/vehicles/admin)."""

import pytest

from app.models.parametersModule.vehicle import Vehicle
from tests.helpers import API

URL = f"{API}/vehicles/admin"


def _rows(response) -> dict[str, dict]:
    assert response.status_code == 200, response.text
    return {row["name"]: row for row in response.json()["items"]}


def _offered(api) -> set[int]:
    """Asignaciones que ofrece el selector de domiciliarios del pedido."""
    response = api.get(f"{API}/users_vehicles/dropdown")
    assert response.status_code == 200, response.text
    return {row["id_user_vehicle"] for row in response.json()}


# --- Listado ----------------------------------------------------------------------


def test_lista_por_nombre_con_asignaciones_activas(admin, db, data):
    db.add(Vehicle(name="NHR TEST"))
    db.commit()

    response = admin.get(URL, params={"search": "test"})

    rows = _rows(response)
    assert list(rows) == ["MOTO TEST", "NHR TEST"]
    assert rows["MOTO TEST"]["assignments_count"] == 1  # el conductor del fixture
    assert rows["NHR TEST"]["assignments_count"] == 0


def test_las_asignaciones_inactivas_no_cuentan(admin, db, data):
    data.user_vehicle.active = False
    db.commit()

    rows = _rows(admin.get(URL, params={"search": "moto test"}))

    assert rows["MOTO TEST"]["assignments_count"] == 0


def test_filtra_por_estado(admin, db, data):
    db.add(Vehicle(name="VIEJO TEST", active=False))
    db.commit()

    active = _rows(admin.get(URL, params={"search": "test", "active": "true"}))
    inactive = _rows(admin.get(URL, params={"search": "test", "active": "false"}))

    assert list(active) == ["MOTO TEST"]
    assert list(inactive) == ["VIEJO TEST"]


# --- Crear ------------------------------------------------------------------------


def test_crea_un_vehiculo(admin):
    response = admin.post(URL, json={"name": "  foton 059 "})

    assert response.status_code == 201, response.text
    assert response.json() == {
        "id_vehicle": response.json()["id_vehicle"],
        "name": "FOTON 059",
        "active": True,
        "assignments_count": 0,
    }


def test_no_se_repite_el_nombre(admin, data):
    # La unicidad ignora mayúsculas y espacios
    response = admin.post(URL, json={"name": "moto  test"})

    assert response.status_code == 409
    assert response.json()["field"] == "name"


@pytest.mark.parametrize("name", ["   ", "x" * 51])
def test_crear_valida_el_nombre(admin, name):
    assert admin.post(URL, json={"name": name}).status_code == 422


# --- Editar, desactivar y reactivar ---------------------------------------------


def test_cambia_el_nombre(admin, data):
    url = f"{URL}/{data.user_vehicle.id_vehicle}"

    response = admin.patch(url, json={"name": "moto 2"})

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "MOTO 2"
    assert response.json()["assignments_count"] == 1


def test_no_cambia_a_un_nombre_de_otro_vehiculo(admin, db, data):
    db.add(Vehicle(name="NHR TEST"))
    db.commit()

    response = admin.patch(
        f"{URL}/{data.user_vehicle.id_vehicle}", json={"name": "NHR TEST"}
    )

    assert response.status_code == 409


def test_desactivar_oculta_sus_asignaciones_y_reactivar_las_devuelve(admin, data):
    url = f"{URL}/{data.user_vehicle.id_vehicle}"
    assignment = data.user_vehicle.id_user_vehicle
    assert assignment in _offered(admin)

    off = admin.patch(url, json={"active": False})
    hidden = assignment not in _offered(admin)
    on = admin.patch(url, json={"active": True})

    assert off.status_code == 200, off.text
    assert off.json()["active"] is False
    assert hidden
    assert on.json()["active"] is True
    assert assignment in _offered(admin)


def test_no_se_vacian_campos_obligatorios(admin, data):
    response = admin.patch(f"{URL}/{data.user_vehicle.id_vehicle}", json={"name": None})

    assert response.status_code == 422
    assert response.json()["code"] == "REQUIRED_FIELD"


def test_editar_vehiculo_inexistente(admin):
    assert admin.patch(f"{URL}/999999", json={"active": False}).status_code == 404


# --- Roles ------------------------------------------------------------------------


def test_el_gestor_no_accede_al_panel_de_vehiculos(client, data):
    assert client.get(URL).status_code == 403
    assert client.post(URL, json={"name": "VANS"}).status_code == 403
    url = f"{URL}/{data.user_vehicle.id_vehicle}"
    assert client.patch(url, json={"active": False}).status_code == 403
