"""Rutas: varios días por ruta (R1) y vista de Rutas (R2)."""

from datetime import time

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.parametersModule.route import Route
from app.schemas.parametersModule.route_schema import RouteCreate, RouteUpdate
from app.services.parametersModule.route_service import route_service
from app.utils.enums.day_week import DayWeek
from tests.helpers import API


def _create_route(db, **overrides) -> Route:
    payload = {"name": "ruta test", "days_week": [1], "departure_time": "06:30"}
    return route_service.create(db, obj_in=RouteCreate(**{**payload, **overrides}))


def test_ruta_con_varios_dias_se_guarda_ordenada_y_sin_repetidos(db):
    route = _create_route(db, days_week=[4, 1, 1])

    db.expire_all()
    assert route.days_week == [DayWeek.MONDAY, DayWeek.THURSDAY]
    assert route.name == "RUTA TEST"
    assert route.departure_time == time(6, 30)


@pytest.mark.parametrize("days", [[], [0], [8]])
def test_dias_invalidos_se_rechazan_en_el_schema(days):
    with pytest.raises(ValidationError):
        RouteCreate(name="ruta", days_week=days, departure_time="06:30")  # type: ignore


def test_actualizar_solo_los_dias(db):
    route = _create_route(db, days_week=[1, 4])

    route_service.update(db, id=route.id_route, obj_in=RouteUpdate(days_week=[7, 6]))  # type: ignore

    db.expire_all()
    assert route.days_week == [6, 7]
    assert route.name == "RUTA TEST"  # lo no enviado no cambia


def test_la_bd_rechaza_una_ruta_sin_dias(db):
    """El CHECK de la BD respalda la validación del schema."""
    db.add(Route(name="SIN DIAS", days_week=[], departure_time=time(8, 0)))

    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- Vista de Rutas (R2): gestión por ADMINISTRADOR, lectura por GESTOR_COMERCIAL --


def _post_route(api, name="ruta norte", days=(1, 4), active=True) -> dict:
    response = api.post(
        f"{API}/routes/",
        json={
            "name": name,
            "days_week": list(days),
            "departure_time": "06:30",
            "active": active,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _new_client(db, data, name, active=True) -> Client:
    new = Client(
        name=name, id_neighborhood=data.neighborhood.id_neighborhood, active=active
    )
    db.add(new)
    db.commit()
    return new


def test_admin_crea_y_edita_rutas(admin):
    route = _post_route(admin, days=(4, 1))
    assert route["days_week"] == [1, 4]
    assert route["name"] == "RUTA NORTE"

    response = admin.patch(
        f"{API}/routes/{route['id_route']}", json={"days_week": [2, 5]}
    )

    assert response.status_code == 200, response.text
    assert response.json()["days_week"] == [2, 5]


# El GESTOR_COMERCIAL solo lee lo que usa su vista de Rutas: cards y clientes de
# cada ruta (y el listado, para filtros). Gestionar rutas es del ADMINISTRADOR.


def test_gestor_lee_las_rutas_y_sus_clientes(client, db, data):
    route = _create_route(db)
    db.add(ClientRoute(id_route=route.id_route, id_client=data.client.id_client))
    db.commit()
    base = f"{API}/routes"

    assert client.get(f"{base}/").status_code == 200
    assert client.get(f"{base}/cards").status_code == 200
    assert client.get(f"{base}/{route.id_route}").status_code == 200
    clients = client.get(f"{base}/{route.id_route}/clients")
    assert clients.status_code == 200
    assert [c["id_client"] for c in clients.json()] == [data.client.id_client]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/", {"name": "ruta x", "days_week": [1], "departure_time": "06:30"}),
        ("patch", "/{id_route}", {"days_week": [2]}),
        ("delete", "/{id_route}", None),
        ("get", "/{id_route}/available-clients", None),
        ("post", "/{id_route}/clients", "assign"),
        ("delete", "/{id_route}/clients/{id_client}", None),
    ],
)
def test_gestor_no_gestiona_rutas(client, db, data, method, path, body):
    route = _create_route(db)
    db.add(ClientRoute(id_route=route.id_route, id_client=data.client.id_client))
    db.commit()
    ids = {"id_route": route.id_route, "id_client": data.client.id_client}
    url = f"{API}/routes" + path.format(**ids)
    if body == "assign":
        body = {"id_client": data.client.id_client}

    kwargs = {"json": body} if body is not None else {}
    response = client.request(method.upper(), url, **kwargs)

    assert response.status_code == 403, response.text


def test_cards_cuentan_solo_clientes_activos(admin, db, data):
    norte = _post_route(admin, name="ruta norte")
    sur = _post_route(admin, name="ruta sur", days=(3,))
    inactive = _new_client(db, data, "CLIENTE INACTIVO", active=False)
    admin.post(
        f"{API}/routes/{norte['id_route']}/clients",
        json={"id_client": data.client.id_client},
    )
    # asignado directamente: la API no permite asignar clientes inactivos
    db.add(ClientRoute(id_route=norte["id_route"], id_client=inactive.id_client))
    db.commit()

    cards = {c["id_route"]: c for c in admin.get(f"{API}/routes/cards").json()}

    assert cards[norte["id_route"]]["clients_count"] == 1
    assert cards[sur["id_route"]]["clients_count"] == 0
    assert cards[norte["id_route"]]["days_week"] == [1, 4]


def test_cards_traen_nombres_y_zonas_de_los_clientes_activos(admin, db, data):
    norte = _post_route(admin, name="ruta norte")
    sur = _post_route(admin, name="ruta sur", days=(3,))
    inactive = _new_client(db, data, "CLIENTE INACTIVO", active=False)
    other = _new_client(db, data, "ALFA CLIENTE")
    admin.post(
        f"{API}/routes/{norte['id_route']}/clients",
        json={"id_client": data.client.id_client},
    )
    # asignados directamente: la API solo asigna clientes registrados y activos
    db.add_all(
        ClientRoute(id_route=norte["id_route"], id_client=c.id_client)
        for c in (other, inactive)
    )
    db.commit()

    cards = {c["id_route"]: c for c in admin.get(f"{API}/routes/cards").json()}

    card = cards[norte["id_route"]]
    assert card["client_names"] == [
        "ALFA CLIENTE",
        "CLIENTE REGISTRADO",
    ]  # A-Z, sin el inactivo
    assert card["zones"] == ["ZONA TEST"]  # sin repetir
    assert len(card["client_names"]) == card["clients_count"]
    assert cards[sur["id_route"]]["client_names"] == []
    assert cards[sur["id_route"]]["zones"] == []


def test_cards_incluyen_rutas_inactivas_salvo_que_se_filtre(admin):
    active = _post_route(admin, name="ruta activa")
    inactive = _post_route(admin, name="ruta inactiva", active=False)

    all_ids = {c["id_route"] for c in admin.get(f"{API}/routes/cards").json()}
    active_ids = {
        c["id_route"] for c in admin.get(f"{API}/routes/cards?only_active=true").json()
    }

    assert {active["id_route"], inactive["id_route"]} <= all_ids
    assert active["id_route"] in active_ids
    assert inactive["id_route"] not in active_ids


def test_asignar_listar_y_quitar_clientes(admin, data):
    route = _post_route(admin)
    url = f"{API}/routes/{route['id_route']}/clients"

    assigned = admin.post(url, json={"id_client": data.client.id_client})
    assert assigned.status_code == 201, assigned.text
    assert assigned.json()["neighborhood_name"] == "BARRIO TEST"
    assert assigned.json()["zone_name"] == "ZONA TEST"

    listed = admin.get(url).json()
    assert [c["id_client"] for c in listed] == [data.client.id_client]

    removed = admin.delete(f"{url}/{data.client.id_client}")
    assert removed.status_code == 204
    assert admin.get(url).json() == []
    assert admin.delete(f"{url}/{data.client.id_client}").status_code == 404


def test_no_se_asigna_dos_veces_el_mismo_cliente(admin, data):
    route = _post_route(admin)
    url = f"{API}/routes/{route['id_route']}/clients"
    admin.post(url, json={"id_client": data.client.id_client})

    response = admin.post(url, json={"id_client": data.client.id_client})

    assert response.status_code == 409


def test_no_se_asigna_un_cliente_inactivo(admin, db, data):
    route = _post_route(admin)
    inactive = _new_client(db, data, "CLIENTE INACTIVO", active=False)

    response = admin.post(
        f"{API}/routes/{route['id_route']}/clients",
        json={"id_client": inactive.id_client},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REFERENCE_INACTIVE"


def test_ruta_inactiva_sigue_gestionando_clientes(admin, data):
    route = _post_route(admin, active=False)

    response = admin.post(
        f"{API}/routes/{route['id_route']}/clients",
        json={"id_client": data.client.id_client},
    )

    assert response.status_code == 201, response.text


def test_clientes_de_ruta_inexistente(admin):
    assert admin.get(f"{API}/routes/999999/clients").status_code == 404


# --- Solo clientes registrados se asignan a rutas ----------------------------------


def test_no_se_asigna_un_cliente_no_registrado(admin, db, data):
    route = _post_route(admin)
    temporary = _new_client(db, data, "CLIENTE DE PASO")  # is_registered=False

    response = admin.post(
        f"{API}/routes/{route['id_route']}/clients",
        json={"id_client": temporary.id_client},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CLIENT_NOT_REGISTERED"


def test_selector_muestra_solo_registrados_activos_y_sin_asignar(admin, db, data):
    route = _post_route(admin)
    url = f"{API}/routes/{route['id_route']}"
    other = _new_client(db, data, "OTRO REGISTRADO")
    other.is_registered = True
    temporary = _new_client(db, data, "CLIENTE DE PASO")
    inactive = _new_client(db, data, "REGISTRADO INACTIVO", active=False)
    inactive.is_registered = True
    db.commit()
    admin.post(f"{url}/clients", json={"id_client": data.client.id_client})

    ids = {c["id_client"] for c in admin.get(f"{url}/available-clients").json()}

    assert other.id_client in ids
    assert data.client.id_client not in ids  # ya asignado
    assert temporary.id_client not in ids  # no registrado
    assert inactive.id_client not in ids  # inactivo


def test_selector_filtra_por_nombre(admin, db, data):
    route = _post_route(admin)
    found = _new_client(db, data, "TIENDA LA ESQUINA")
    found.is_registered = True
    db.commit()

    response = admin.get(
        f"{API}/routes/{route['id_route']}/available-clients?name=esquina"
    )

    assert response.status_code == 200, response.text
    assert [c["id_client"] for c in response.json()] == [found.id_client]
