"""Vista Histórico: GET /orders/history (H2)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from app.core.timezone import BOGOTA_TZ, today_bogota
from app.models.coreModule.order import Order
from app.models.parametersModule.route import Route
from tests.helpers import API, item, mark_cancelled

URL = f"{API}/orders/history"


def _move(db, order: dict, day: date, hour: int = 10) -> None:
    """Cambia la fecha de un pedido: creación y entrega (hora local de Bogotá)."""
    row = db.get(Order, order["id_order"])
    row.creation_datetime = datetime.combine(day, time(hour, 0), tzinfo=BOGOTA_TZ)
    row.delivery_date = day
    db.commit()


def _ids(response) -> list[int]:
    assert response.status_code == 200, response.text
    return [row["id_order"] for row in response.json()["items"]]


def _first_of_previous_month(today: date) -> date:
    return (today.replace(day=1) - timedelta(days=1)).replace(day=1)


def test_lista_los_pedidos_con_sus_datos_y_totales(client, create_order, data):
    order = create_order(
        items=[item(data.products[0], 2), item(data.products[1], 1)],
        id_user_vehicle=data.user_vehicle.id_user_vehicle,
    )

    response = client.get(URL)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["date_to"] == today_bogota().isoformat()
    assert body["date_from"] == _first_of_previous_month(today_bogota()).isoformat()
    assert body["total"] == 1
    assert body["pages"] == 1
    assert Decimal(body["total_sales"]) == Decimal("12000.00")
    row = body["items"][0]
    assert row["id_order"] == order["id_order"]
    assert row["order_date"] == today_bogota().isoformat()
    assert row["client_name"] == "CLIENTE REGISTRADO"
    assert row["zone_name"] == "ZONA TEST"
    assert row["route_name"] is None
    assert row["total_quantity"] == 3
    assert set(row["product_codes"].split(", ")) == {"Z91", "Z92"}
    assert row["driver_code"] == "99"
    assert row["driver_name"] == "Carlos Conductor"
    assert row["state"] == "PENDING"


def test_por_defecto_incluye_mes_anterior_y_excluye_lo_mas_viejo(
    client, create_order, db
):
    today = today_bogota()
    previous_month = create_order()
    too_old = create_order()
    current = create_order()
    _move(db, previous_month, _first_of_previous_month(today))
    _move(db, too_old, _first_of_previous_month(today) - timedelta(days=1))

    ids = _ids(client.get(URL))

    assert current["id_order"] in ids
    assert previous_month["id_order"] in ids
    assert too_old["id_order"] not in ids


def test_filtro_por_rango_de_fechas_incluye_ambos_extremos(client, create_order, db):
    day_1, day_2, day_3 = (date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 12))
    orders = [create_order() for _ in range(3)]
    _move(db, orders[0], day_1, hour=0)  # 00:00 del 10
    _move(db, orders[1], day_2, hour=23)  # 23:00 del 11
    _move(db, orders[2], day_3)

    ids = _ids(client.get(f"{URL}?date_from={day_1}&date_to={day_2}"))

    assert set(ids) == {orders[0]["id_order"], orders[1]["id_order"]}


def test_ordenado_del_mas_antiguo_al_mas_nuevo_y_paginado(client, create_order, db):
    orders = [create_order() for _ in range(3)]
    for hour, order in zip((10, 8, 9), orders, strict=True):
        _move(db, order, today_bogota(), hour=hour)

    page_1 = client.get(f"{URL}?page_size=2").json()
    page_2 = client.get(f"{URL}?page_size=2&page=2").json()

    expected = [orders[1]["id_order"], orders[2]["id_order"], orders[0]["id_order"]]
    assert [r["id_order"] for r in page_1["items"]] == expected[:2]
    assert [r["id_order"] for r in page_2["items"]] == expected[2:]
    assert (page_1["total"], page_1["pages"]) == (3, 2)


def test_sort_dir_desc_vuelve_al_mas_reciente_primero(client, create_order, db):
    older, newer = create_order(), create_order()
    _move(db, older, today_bogota() - timedelta(days=1))
    _move(db, newer, today_bogota())

    assert _ids(client.get(URL))[:2] == [older["id_order"], newer["id_order"]]
    assert _ids(client.get(f"{URL}?sort_dir=desc"))[:2] == [
        newer["id_order"],
        older["id_order"],
    ]


def test_ordenar_por_cliente_y_total(client, create_order, data):
    small = create_order(items=[item(data.products[0], 1)])  # 3000
    big = create_order(items=[item(data.products[2], 1)])  # 8000
    other = client.post(
        f"{API}/orders/new-client",
        json={
            "client": {
                "name": "aaa primero",
                "id_neighborhood": data.neighborhood.id_neighborhood,
            },
            "items": [item(data.products[1], 1)],  # 6000
        },
    ).json()

    by_client = _ids(client.get(f"{URL}?sort_by=client_name"))
    by_total = _ids(client.get(f"{URL}?sort_by=total&sort_dir=desc"))

    assert by_client[0] == other["id_order"]  # "AAA PRIMERO" antes de "CLIENTE ..."
    assert by_total == [big["id_order"], other["id_order"], small["id_order"]]


def test_campo_de_orden_invalido(client):
    unknown = client.get(f"{URL}?sort_by=password")
    malformed = client.get(f"{URL}?sort_by=Client.name")

    assert unknown.status_code == 422
    assert unknown.json()["code"] == "INVALID_SORT_FIELD"
    assert "client_name" in unknown.json()["detail"]
    assert malformed.status_code == 422  # el patrón solo admite a-z y _


def test_filas_traen_pago_y_factura_y_se_filtran(client, create_order):
    cash = create_order()
    transfer = create_order(payment_method="TRANSFER", invoice_type="ELECTRONIC")

    rows = {r["id_order"]: r for r in client.get(URL).json()["items"]}
    only_transfer = _ids(client.get(f"{URL}?payment_method=TRANSFER"))
    only_electronic = _ids(client.get(f"{URL}?invoice_type=ELECTRONIC"))

    cash_row = rows[cash["id_order"]]
    assert (cash_row["payment_method"], cash_row["invoice_type"]) == ("CASH", "POS")
    assert only_transfer == [transfer["id_order"]]
    assert only_electronic == [transfer["id_order"]]


def test_filtros_por_estado_ruta_y_conductor(client, create_order, db, data):
    route = Route(name="RUTA HISTORICO", days_week=[1], departure_time=time(6, 0))
    db.add(route)
    db.commit()
    with_driver = create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle)
    dispatched = create_order()
    on_route = create_order()
    client.post(f"{API}/orders/{dispatched['id_order']}/dispatch")
    db.get(Order, on_route["id_order"]).id_route = route.id_route
    db.commit()

    assert _ids(client.get(f"{URL}?state=DISPATCHED")) == [dispatched["id_order"]]
    assert _ids(client.get(f"{URL}?id_route={route.id_route}")) == [on_route["id_order"]]
    assert _ids(
        client.get(f"{URL}?id_user_vehicle={data.user_vehicle.id_user_vehicle}")
    ) == [with_driver["id_order"]]


def test_busqueda_por_cliente_o_numero_de_pedido(client, create_order, data):
    first = create_order()
    second = create_order()
    new_client = client.post(
        f"{API}/orders/new-client",
        json={
            "client": {
                "name": "tienda la esquina",
                "id_neighborhood": data.neighborhood.id_neighborhood,
            },
            "items": [item(data.products[0], 1)],
        },
    ).json()

    assert _ids(client.get(f"{URL}?search=esquina")) == [new_client["id_order"]]
    assert _ids(client.get(f"{URL}?search={second['purchase_order']}")) == [
        second["id_order"]
    ]
    assert first["id_order"] in _ids(client.get(f"{URL}?search=registrado"))


def test_ventas_del_filtro_excluyen_cancelados(client, create_order, db, data):
    kept = create_order(items=[item(data.products[0], 1)])  # 3000
    cancelled = create_order(items=[item(data.products[2], 1)])  # 8000
    mark_cancelled(db, cancelled["id_order"])
    db.commit()

    body = client.get(URL).json()

    assert body["total"] == 2  # el cancelado se lista...
    assert Decimal(body["total_sales"]) == Decimal(kept["order_total"])  # ...no suma


def test_rango_invertido_responde_422(client):
    response = client.get(f"{URL}?date_from=2026-10-10&date_to=2026-10-01")

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_DATE_RANGE"


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=201"])
def test_paginacion_invalida(client, query):
    assert client.get(f"{URL}?{query}").status_code == 422


def test_sin_resultados(client):
    body = client.get(f"{URL}?date_from=2020-01-01&date_to=2020-01-31").json()

    assert (body["total"], body["pages"], body["items"]) == (0, 0, [])
    assert Decimal(body["total_sales"]) == Decimal(0)
