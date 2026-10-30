"""Un pedido solo se asigna (al crear o al reasignar) a un domiciliario cuya
asignación, vehículo y usuario estén activos. Un pedido que ya lo tenía lo
conserva."""

import pytest

from tests.helpers import API, item


@pytest.fixture()
def assignment(data):
    return data.user_vehicle.id_user_vehicle


def _deactivate(db, data, what: str) -> None:
    if what == "assignment":
        data.user_vehicle.active = False
    elif what == "vehicle":
        data.user_vehicle.vehicle.active = False
    elif what == "user":
        data.user_vehicle.user_role.user.active = False
    elif what == "person":
        data.user_vehicle.user_role.user.person.active = False
    db.commit()


INACTIVE = ["assignment", "vehicle", "user", "person"]


@pytest.mark.parametrize("what", INACTIVE)
def test_no_se_crea_un_pedido_con_un_domiciliario_inactivo(
    client, db, data, assignment, what
):
    _deactivate(db, data, what)

    response = client.post(
        f"{API}/orders/existing-client",
        json={
            "id_client": data.client.id_client,
            "id_user_vehicle": assignment,
            "items": [item(data.products[0], 1)],
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "REFERENCE_INACTIVE"
    assert response.json()["field"] == "id_user_vehicle"


@pytest.mark.parametrize("what", INACTIVE)
def test_no_se_reasigna_a_un_domiciliario_inactivo(
    client, db, data, assignment, create_order, what
):
    order = create_order()
    _deactivate(db, data, what)

    response = client.patch(
        f"{API}/orders/{order['id_order']}", json={"id_user_vehicle": assignment}
    )

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "REFERENCE_INACTIVE"


def test_el_pedido_conserva_su_domiciliario_aunque_se_desactive(
    client, db, data, assignment, create_order
):
    order = create_order(id_user_vehicle=assignment)
    _deactivate(db, data, "vehicle")

    # Editar otro campo (la hora) y reenviar el mismo domiciliario no falla
    response = client.patch(
        f"{API}/orders/{order['id_order']}",
        json={"estimated_delivery": "10:30", "id_user_vehicle": assignment},
    )
    dispatched = client.post(f"{API}/orders/{order['id_order']}/dispatch")

    assert response.status_code == 200, response.text
    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json()["id_user_vehicle"] == assignment


def test_domiciliario_inexistente(client, create_order):
    order = create_order()

    response = client.patch(
        f"{API}/orders/{order['id_order']}", json={"id_user_vehicle": 999_999}
    )

    assert response.status_code == 422
    assert response.json()["field"] == "id_user_vehicle"
