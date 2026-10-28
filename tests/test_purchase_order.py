"""purchase_order: consecutivo diario (hora de Bogotá) asignado por el servidor (R3)."""

from datetime import timedelta

from sqlalchemy import func, select, text

from app.models.coreModule.daily_order_counter import DailyOrderCounter
from app.models.coreModule.order import Order
from tests.helpers import API, item

# Mismo "hoy" que usa el servidor: now() es la hora de inicio de la transacción,
# y el test y las peticiones comparten la misma transacción.
TODAY_SQL = "(now() AT TIME ZONE 'America/Bogota')::date"


def _today(db):
    return db.scalar(text(f"SELECT {TODAY_SQL}"))


def _set_counter(db, day, value: int) -> None:
    db.execute(
        text(
            "INSERT INTO daily_order_counter (counter_date, last_value) "
            "VALUES (:day, :value) "
            "ON CONFLICT (counter_date) DO UPDATE SET last_value = :value"
        ),
        {"day": day, "value": value},
    )
    db.commit()


def test_pedidos_del_dia_reciben_numeros_consecutivos(create_order):
    first = create_order()
    second = create_order()
    third = create_order()

    numbers = [int(o["purchase_order"]) for o in (first, second, third)]
    assert numbers == [numbers[0], numbers[0] + 1, numbers[0] + 2]
    assert all(len(o["purchase_order"]) == 3 for o in (first, second, third))


def test_primer_pedido_del_dia_es_001(create_order):
    assert create_order()["purchase_order"] == "001"


def test_el_numero_enviado_por_el_cliente_se_ignora(create_order):
    order = create_order(purchase_order="777")

    assert order["purchase_order"] == "001"


def test_cliente_nuevo_y_existente_comparten_el_consecutivo(client, data, create_order):
    existing = create_order()
    response = client.post(
        f"{API}/orders/new-client",
        json={
            "client": {
                "name": "cliente de paso",
                "id_neighborhood": data.neighborhood.id_neighborhood,
            },
            "items": [item(data.products[0], 1)],
        },
    )

    assert response.status_code == 201, response.text
    assert int(response.json()["purchase_order"]) == int(existing["purchase_order"]) + 1


def test_pedidos_de_dias_anteriores_conservan_su_numero(db, create_order):
    today = _today(db)
    yesterday = today - timedelta(days=1)
    _set_counter(db, yesterday, 50)

    old = create_order()  # recibe 001 de hoy; lo movemos a ayer
    old_row = db.get(Order, old["id_order"])
    old_row.creation_datetime -= timedelta(days=1)
    old_row.delivery_date = yesterday
    db.commit()

    create_order()
    create_order()

    db.expire_all()
    assert db.get(Order, old["id_order"]).purchase_order == old["purchase_order"]
    assert db.get(DailyOrderCounter, yesterday).last_value == 50  # ayer intacto
    assert db.get(DailyOrderCounter, today).last_value == 3


def test_limite_de_999_pedidos_por_dia(client, db, data):
    today = _today(db)
    _set_counter(db, today, 999)
    before = db.scalar(select(func.count()).select_from(Order))

    response = client.post(
        f"{API}/orders/existing-client",
        json={"id_client": data.client.id_client, "items": [item(data.products[0], 1)]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "DAILY_ORDER_LIMIT"
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Order)) == before
    assert db.get(DailyOrderCounter, today).last_value == 999  # no avanzó


def test_un_pedido_fallido_no_consume_numero(client, db, data, create_order):
    first = create_order()
    failed = client.post(
        f"{API}/orders/existing-client",
        json={
            "id_client": data.client.id_client,
            "items": [item(data.products[0], 1), item(data.products[0], 2)],  # repetido
        },
    )
    assert failed.status_code == 422

    second = create_order()

    assert int(second["purchase_order"]) == int(first["purchase_order"]) + 1
