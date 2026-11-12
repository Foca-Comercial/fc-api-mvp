"""Cambios finales B8: ordenamiento en el servidor de los listados paginados.

`sort_by` / `sort_dir` llegan por `get_page_params` y cada repositorio declara sus
campos ordenables con `order_clause` (lista blanca + PK como desempate).
"""

from datetime import time

import pytest
from sqlalchemy import select

from app.models.coreModule.client import Client
from app.models.coreModule.client_route import ClientRoute
from app.models.coreModule.product import Product
from app.models.parametersModule.route import Route
from app.models.parametersModule.vehicle import Vehicle
from app.repositories.pagination import order_clause
from app.schemas.common.page_schema import PageParams
from app.utils.exceptions.business_exceptions import BusinessValidationError
from tests.helpers import API


def _names(response, key="name") -> list:
    assert response.status_code == 200, response.text
    return [row[key] for row in response.json()["items"]]


# --- order_clause ----------------------------------------------------------------------


def test_sin_sort_by_usa_el_orden_por_defecto_y_la_pk(db, data):
    clause = order_clause(
        PageParams(),
        {"code": Product.code},
        default=[Product.code],
        tiebreak=Product.id_product,
    )
    stmt = select(Product.code).where(Product.code.startswith("Z9")).order_by(*clause)

    assert list(db.scalars(stmt)) == ["Z91", "Z92", "Z93"]


def test_sort_dir_desc_invierte_tambien_el_desempate(db, data):
    clause = order_clause(
        PageParams(sort_dir="desc"),
        {"code": Product.code},
        default=[Product.code],
        tiebreak=Product.id_product,
    )
    stmt = select(Product.code).where(Product.code.startswith("Z9")).order_by(*clause)

    assert list(db.scalars(stmt)) == ["Z93", "Z92", "Z91"]


def test_campo_fuera_de_la_lista_blanca():
    with pytest.raises(BusinessValidationError) as error:
        order_clause(
            PageParams(sort_by="password"),
            {"name": Client.name},
            default=[Client.name],
            tiebreak=Client.id_client,
        )

    assert error.value.code == "INVALID_SORT_FIELD"
    assert error.value.field == "sort_by"


# --- Listados del panel ----------------------------------------------------------------


def test_clientes_por_nombre_y_por_cantidad_de_rutas(admin, db, data):
    first = Client(
        name="AAA ORDEN",
        id_neighborhood=data.neighborhood.id_neighborhood,
        is_registered=True,
    )
    last = Client(
        name="ZZZ ORDEN",
        id_neighborhood=data.neighborhood.id_neighborhood,
        is_registered=True,
    )
    route = Route(name="RUTA ORDEN", days_week=[1], departure_time=time(6, 0))
    db.add_all([first, last, route])
    db.flush()
    db.add(ClientRoute(id_route=route.id_route, id_client=last.id_client))
    db.commit()
    url = f"{API}/clients/admin?search=orden"

    assert _names(admin.get(url)) == ["AAA ORDEN", "ZZZ ORDEN"]
    assert _names(admin.get(f"{url}&sort_by=name&sort_dir=desc")) == [
        "ZZZ ORDEN",
        "AAA ORDEN",
    ]
    # Campo calculado (alias del SELECT)
    assert _names(admin.get(f"{url}&sort_by=routes_count&sort_dir=desc")) == [
        "ZZZ ORDEN",
        "AAA ORDEN",
    ]


def test_productos_por_precio_base(admin, data):
    url = f"{API}/products/admin?search=Z9&sort_by=base_price&sort_dir=desc"
    response = admin.get(url)

    assert _names(response, "code") == ["Z93", "Z92", "Z91"]


def test_vehiculos_por_nombre_descendente(admin, db):
    db.add_all([Vehicle(name="ORDEN A"), Vehicle(name="ORDEN B")])
    db.commit()

    url = f"{API}/vehicles/admin?search=orden&sort_by=name&sort_dir=desc"
    response = admin.get(url)

    assert _names(response) == ["ORDEN B", "ORDEN A"]


def test_rutas_por_cantidad_de_clientes(admin, db, data):
    empty = Route(name="ORDEN VACIA", days_week=[1], departure_time=time(6, 0))
    full = Route(name="ORDEN LLENA", days_week=[1], departure_time=time(7, 0))
    db.add_all([empty, full])
    db.flush()
    db.add(ClientRoute(id_route=full.id_route, id_client=data.client.id_client))
    db.commit()
    url = f"{API}/routes/admin?search=orden"

    assert _names(admin.get(url)) == ["ORDEN LLENA", "ORDEN VACIA"]  # por nombre
    assert _names(admin.get(f"{url}&sort_by=clients_count")) == [
        "ORDEN VACIA",
        "ORDEN LLENA",
    ]


@pytest.mark.parametrize(
    "path",
    [
        "/clients/admin",
        "/products/admin",
        "/drivers/admin",
        "/vehicles/admin",
        "/routes/admin",
    ],
)
def test_campo_invalido_en_cada_listado(admin, path):
    response = admin.get(f"{API}{path}?sort_by=no_existe")

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SORT_FIELD"


def test_sort_dir_invalido(admin):
    assert admin.get(f"{API}/clients/admin?sort_dir=up").status_code == 422
