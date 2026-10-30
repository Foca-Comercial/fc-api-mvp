"""Panel de administración: domiciliarios (usuarios VENDEDOR) y sus asignaciones con
vehículos (/drivers/admin)."""

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.parametersModule.vehicle import Vehicle
from app.models.securityModule.role import Role
from app.models.securityModule.user import User
from app.models.securityModule.user_role import UserRole
from app.utils.helpers.password_helper import verify_password
from tests.helpers import API, item

URL = f"{API}/drivers/admin"


@pytest.fixture()
def seller_role(db):
    """El rol VENDEDOR (la BD de pruebas no tiene seeds)."""
    role = db.scalar(select(Role).where(Role.name == "VENDEDOR"))
    if role is None:
        role = Role(name="VENDEDOR")
        db.add(role)
        db.commit()
    return role


@pytest.fixture()
def vehicles(db):
    nhr = Vehicle(name="NHR TEST")
    vans = Vehicle(name="VANS TEST")
    db.add_all([nhr, vans])
    db.commit()
    return nhr, vans


def _driver(api, name="Pedro", last_name="Pérez", **extra) -> dict:
    response = api.post(URL, json={"name": name, "last_name": last_name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def _assign(api, id_user, id_vehicle, code="45"):
    return api.post(
        f"{URL}/{id_user}/assignments", json={"id_vehicle": id_vehicle, "code": code}
    )


# --- Crear ------------------------------------------------------------------------


def test_crea_persona_usuario_y_rol(admin, db, seller_role):
    body = _driver(admin, phone="3001234567", email="pedro@correo.com")

    assert body["name"] == "PEDRO"
    assert body["last_name"] == "PÉREZ"
    assert body["username"] == "pedro.perez"
    assert (body["active"], body["codes"], body["assignments_count"]) == (True, [], 0)
    assert body["protected"] is False
    user = db.get(User, body["id_user"])
    assert verify_password("contrasena", user.password)
    roles = db.scalars(select(UserRole.id_role).where(UserRole.id_user == user.id_user))
    assert list(roles) == [seller_role.id_role]


def test_el_usuario_no_se_repite(admin, seller_role):
    first = _driver(admin)
    second = _driver(admin)
    accents = _driver(admin, name="José Luis", last_name="Peña Rojas")

    assert first["username"] == "pedro.perez"
    assert second["username"] == "pedro.perez2"
    assert accents["username"] == "jose.pena"


def test_sin_rol_vendedor_no_se_crea(admin, db):
    assert db.scalar(select(Role).where(Role.name == "VENDEDOR")) is None

    response = admin.post(URL, json={"name": "Pedro", "last_name": "Pérez"})

    assert response.status_code == 422
    assert response.json()["code"] == "SELLER_ROLE_MISSING"


@pytest.mark.parametrize(
    "body",
    [
        {"phone": "123"},
        {"email": "no-es-correo"},
        {"name": "   "},
    ],
)
def test_crear_valida_los_campos(admin, seller_role, body):
    payload = {"name": "Pedro", "last_name": "Pérez", **body}

    assert admin.post(URL, json=payload).status_code == 422


# --- Listado ----------------------------------------------------------------------


def test_lista_solo_vendedores_con_sus_codigos_activos(
    admin, db, seller_role, vehicles
):
    nhr, vans = vehicles
    driver = _driver(admin)
    _assign(admin, driver["id_user"], vans.id_vehicle, "47")
    retired = _assign(admin, driver["id_user"], nhr.id_vehicle, "46").json()
    admin.patch(
        f"{URL}/{driver['id_user']}/assignments/{retired['id_user_vehicle']}",
        json={"active": False},
    )

    page = admin.get(URL).json()

    # El conductor del fixture `data` no tiene el rol VENDEDOR: no aparece
    assert [row["id_user"] for row in page["items"]] == [driver["id_user"]]
    assert page["items"][0]["codes"] == ["47"]
    assert page["items"][0]["assignments_count"] == 1


def test_busca_por_nombre_o_codigo_y_filtra_estado(admin, seller_role, vehicles):
    pedro = _driver(admin)
    ana = _driver(admin, name="Ana", last_name="Gómez")
    _assign(admin, ana["id_user"], vehicles[0].id_vehicle, "61")
    admin.patch(f"{URL}/{pedro['id_user']}", json={"active": False})

    def ids(**params):
        response = admin.get(URL, params=params)
        assert response.status_code == 200, response.text
        return [row["id_user"] for row in response.json()["items"]]

    # Sin tildes: con un locale "C" ILIKE no iguala mayúsculas y minúsculas acentuadas
    assert ids(search="ana g") == [ana["id_user"]]
    assert ids(search="pedro p") == [pedro["id_user"]]
    assert ids(search="6") == [ana["id_user"]]
    assert ids(active="false") == [pedro["id_user"]]
    assert ids(active="true") == [ana["id_user"]]


# --- Editar, desactivar y reactivar ---------------------------------------------


def test_edicion_parcial_de_la_persona(admin, seller_role):
    driver = _driver(admin)

    url = f"{URL}/{driver['id_user']}"

    response = admin.patch(url, json={"phone": "3109998877"})

    assert response.status_code == 200, response.text
    assert response.json()["phone"] == "3109998877"
    assert response.json()["name"] == "PEDRO"
    assert response.json()["username"] == "pedro.perez"  # no cambia al editar


def test_desactivar_oculta_sus_asignaciones_del_selector(
    admin, db, seller_role, vehicles
):
    driver = _driver(admin)
    assignment = _assign(admin, driver["id_user"], vehicles[0].id_vehicle).json()

    off = admin.patch(f"{URL}/{driver['id_user']}", json={"active": False})
    dropdown = admin.get(f"{API}/users_vehicles/dropdown").json()
    on = admin.patch(f"{URL}/{driver['id_user']}", json={"active": True})

    assert off.status_code == 200, off.text
    assert off.json()["active"] is False
    offered = {d["id_user_vehicle"] for d in dropdown}
    assert assignment["id_user_vehicle"] not in offered
    assert on.json()["active"] is True
    user = db.get(User, driver["id_user"])
    db.refresh(user)
    assert user.active is True and user.person.active is True


def test_no_se_desactiva_un_usuario_con_otro_rol(admin, db, seller_role):
    driver = _driver(admin)
    other = Role(name="ROL_TEST_OTRO")
    db.add(other)
    db.flush()
    db.add(UserRole(id_user=driver["id_user"], id_role=other.id_role))
    db.commit()

    listed = admin.get(URL).json()["items"][0]
    response = admin.patch(f"{URL}/{driver['id_user']}", json={"active": False})

    assert listed["protected"] is True
    assert response.status_code == 422
    assert response.json()["code"] == "DRIVER_PROTECTED"


def test_no_se_vacian_campos_obligatorios(admin, seller_role):
    driver = _driver(admin)

    response = admin.patch(f"{URL}/{driver['id_user']}", json={"name": None})

    assert response.status_code == 422
    assert response.json()["code"] == "REQUIRED_FIELD"


def test_un_usuario_que_no_es_vendedor_no_se_gestiona(admin, data, seller_role):
    url = f"{URL}/{data.taker.id_user}"

    assert admin.patch(url, json={"phone": "3001234567"}).status_code == 404
    assert admin.get(f"{url}/assignments").status_code == 404


# --- Asignaciones -----------------------------------------------------------------


def test_crea_y_lista_asignaciones(admin, seller_role, vehicles):
    nhr, vans = vehicles
    driver = _driver(admin)

    created = _assign(admin, driver["id_user"], vans.id_vehicle, "47")
    _assign(admin, driver["id_user"], nhr.id_vehicle, "46")
    listed = admin.get(f"{URL}/{driver['id_user']}/assignments").json()

    assert created.status_code == 201, created.text
    assert created.json()["vehicle_name"] == "VANS TEST"
    assert (created.json()["in_use"], created.json()["is_default"]) == (False, False)
    assert [(a["code"], a["vehicle_name"]) for a in listed] == [
        ("46", "NHR TEST"),
        ("47", "VANS TEST"),
    ]


def test_codigo_y_pareja_unicos(admin, data, seller_role, vehicles):
    driver = _driver(admin)
    _assign(admin, driver["id_user"], vehicles[0].id_vehicle, "45")

    # "99" es del conductor del fixture `data`
    taken = _assign(admin, driver["id_user"], vehicles[1].id_vehicle, "99")
    same_pair = _assign(admin, driver["id_user"], vehicles[0].id_vehicle, "46")

    assert taken.status_code == 409
    assert taken.json()["code"] == "SELLER_CODE_TAKEN"
    assert same_pair.status_code == 409
    assert same_pair.json()["code"] == "DUPLICATE_ASSIGNMENT"


@pytest.mark.parametrize("code", ["5", "123", "AB"])
def test_codigo_de_dos_digitos(admin, seller_role, vehicles, code):
    driver = _driver(admin)

    response = _assign(admin, driver["id_user"], vehicles[0].id_vehicle, code)

    assert response.status_code == 422


def test_no_se_asigna_un_vehiculo_inactivo(admin, db, seller_role, vehicles):
    vehicles[0].active = False
    db.commit()
    driver = _driver(admin)

    response = _assign(admin, driver["id_user"], vehicles[0].id_vehicle)

    assert response.status_code == 422
    assert response.json()["code"] == "REFERENCE_INACTIVE"


def test_sin_uso_cambia_codigo_y_vehiculo_y_se_borra(admin, seller_role, vehicles):
    driver = _driver(admin)
    created = _assign(admin, driver["id_user"], vehicles[0].id_vehicle, "45").json()
    url = f"{URL}/{driver['id_user']}/assignments/{created['id_user_vehicle']}"

    edited = admin.patch(
        url, json={"code": "48", "id_vehicle": vehicles[1].id_vehicle}
    )
    removed = admin.delete(url)

    assert edited.status_code == 200, edited.text
    assert edited.json()["code"] == "48"
    assert edited.json()["vehicle_name"] == "VANS TEST"
    assert removed.status_code == 204
    assert admin.get(f"{URL}/{driver['id_user']}/assignments").json() == []


def test_con_pedidos_solo_cambia_el_estado(admin, seller_role, vehicles, create_order):
    driver = _driver(admin)
    created = _assign(admin, driver["id_user"], vehicles[0].id_vehicle, "45").json()
    create_order(id_user_vehicle=created["id_user_vehicle"])
    url = f"{URL}/{driver['id_user']}/assignments/{created['id_user_vehicle']}"

    code = admin.patch(url, json={"code": "48"})
    vehicle = admin.patch(url, json={"id_vehicle": vehicles[1].id_vehicle})
    removed = admin.delete(url)
    off = admin.patch(url, json={"active": False})

    for response in (code, vehicle, removed):
        assert response.status_code == 422
        assert response.json()["code"] == "ASSIGNMENT_IN_USE"
    assert off.status_code == 200, off.text
    assert (off.json()["active"], off.json()["in_use"]) == (False, True)


def test_una_asignacion_inactiva_no_recibe_pedidos(
    admin, data, seller_role, vehicles
):
    driver = _driver(admin)
    created = _assign(admin, driver["id_user"], vehicles[0].id_vehicle).json()
    admin.patch(
        f"{URL}/{driver['id_user']}/assignments/{created['id_user_vehicle']}",
        json={"active": False},
    )

    response = admin.post(
        f"{API}/orders/existing-client",
        json={
            "id_client": data.client.id_client,
            "id_user_vehicle": created["id_user_vehicle"],
            "items": [item(data.products[0], 1)],
        },
    )
    dropdown = admin.get(f"{API}/users_vehicles/dropdown").json()

    assert response.status_code == 422
    assert response.json()["code"] == "REFERENCE_INACTIVE"
    assert created["id_user_vehicle"] not in {d["id_user_vehicle"] for d in dropdown}


def test_vendedor_por_defecto_protegido(admin, seller_role, vehicles, monkeypatch):
    monkeypatch.setattr(settings, "DEFAULT_SELLER_CODE", "09")
    driver = _driver(admin, name="Hielo", last_name="Foca")
    created = _assign(admin, driver["id_user"], vehicles[0].id_vehicle, "09").json()
    url = f"{URL}/{driver['id_user']}/assignments/{created['id_user_vehicle']}"

    responses = [
        admin.patch(url, json={"active": False}),
        admin.patch(url, json={"code": "10"}),
        admin.delete(url),
        admin.patch(f"{URL}/{driver['id_user']}", json={"active": False}),
    ]

    assert created["is_default"] is True
    assert admin.get(URL).json()["items"][0]["protected"] is True
    for response in responses:
        assert response.status_code == 422
        assert response.json()["code"] == "DEFAULT_SELLER_PROTECTED"


def test_asignacion_de_otro_domiciliario(admin, seller_role, vehicles):
    owner = _driver(admin)
    other = _driver(admin, name="Ana", last_name="Gómez")
    created = _assign(admin, owner["id_user"], vehicles[0].id_vehicle).json()
    url = f"{URL}/{other['id_user']}/assignments/{created['id_user_vehicle']}"

    assert admin.patch(url, json={"active": False}).status_code == 404
    assert admin.delete(url).status_code == 404


def test_sugiere_el_siguiente_codigo_libre(admin, db, seller_role, vehicles):
    assert admin.get(f"{URL}/next-code").json() == {"code": "01"}

    driver = _driver(admin)
    _assign(admin, driver["id_user"], vehicles[0].id_vehicle, "01")
    _assign(admin, driver["id_user"], vehicles[1].id_vehicle, "02")

    assert admin.get(f"{URL}/next-code").json() == {"code": "03"}


# --- Roles ------------------------------------------------------------------------


def test_el_gestor_no_accede_al_panel_de_domiciliarios(client, data):
    assert client.get(URL).status_code == 403
    assert client.post(URL, json={"name": "A", "last_name": "B"}).status_code == 403
    assert client.get(f"{URL}/next-code").status_code == 403
