"""Vista de Cierre: CRUD de solo lectura (C1), resumen (C2) y exportación (C3)."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.timezone import BOGOTA_TZ, today_bogota
from app.models.coreModule.order import Order
from app.models.coreModule.shift_closure import ShiftClosure
from app.repositories.coreModule.shift_closure_repository import (
    shift_closure_repository,
)
from app.services.coreModule.closure_export import MEDIA_TYPE
from tests.helpers import API, item, mark_cancelled

URL = f"{API}/shifts_closures"


def test_el_crud_es_de_solo_lectura(admin):
    assert admin.get(f"{URL}/").status_code == 200
    assert admin.post(f"{URL}/", json={}).status_code == 405
    assert admin.patch(f"{URL}/1", json={}).status_code == 405
    assert admin.delete(f"{URL}/1").status_code == 405


def test_un_cierre_por_vendedor_y_dia(db, data):
    def closure():
        return ShiftClosure(
            closure_date=date(2026, 10, 15),
            id_user_vehicle=data.user_vehicle.id_user_vehicle,
            total_orders=1,
            total_sales=Decimal(1000),
        )

    db.add(closure())
    db.flush()
    db.add(closure())

    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- Resumen del cierre (C2): GET /shifts_closures/summary ---------------------------

SUMMARY = f"{URL}/summary"


def _dispatch(client, order: dict, deliver: bool = False) -> None:
    response = client.post(f"{API}/orders/{order['id_order']}/dispatch")
    assert response.status_code == 200, response.text
    if deliver:
        response = client.post(f"{API}/orders/{order['id_order']}/deliver")
        assert response.status_code == 200, response.text


def _move(db, order: dict, day: date) -> None:
    row = db.get(Order, order["id_order"])
    row.creation_datetime = datetime.combine(day, time(10, 0), tzinfo=BOGOTA_TZ)
    row.delivery_date = day
    db.commit()


def _summary(client, day: date | None = None) -> dict:
    url = SUMMARY if day is None else f"{SUMMARY}?target_date={day}"
    response = client.get(url)
    assert response.status_code == 200, response.text
    return response.json()


def test_resumen_consolida_por_vendedor_y_cuenta_estados(
    client, create_order, db, data, default_seller
):
    driver = data.user_vehicle.id_user_vehicle
    p0, p1, p2 = data.products
    a = create_order(items=[item(p0, 2), item(p1, 1)], id_user_vehicle=driver)  # 12000
    b = create_order(items=[item(p0, 1, "2500.00")], id_user_vehicle=driver)  # 2500
    c = create_order(items=[item(p2, 1)])  # 8000, sin conductor
    create_order(id_user_vehicle=driver)  # queda pendiente
    cancelled = create_order(id_user_vehicle=driver)
    _dispatch(client, a)
    _dispatch(client, b, deliver=True)
    _dispatch(client, c)
    mark_cancelled(db, cancelled["id_order"])
    db.commit()

    body = _summary(client)

    assert body["closure_date"] == today_bogota().isoformat()
    cards = body["cards"]
    assert (cards["total_orders"], cards["pending"], cards["cancelled"]) == (5, 1, 1)
    assert (cards["dispatched"], cards["delivered"]) == (2, 1)
    assert cards["sellers_count"] == 2
    assert Decimal(cards["total_income"]) == Decimal(22500)
    assert body["exported"] is False

    default_row, driver_row = body["sellers"]  # ordenados por código: 9, 99
    assert (default_row["seller_code"], default_row["seller_name"]) == (9, "Hielo Foca")
    assert default_row["orders_count"] == default_row["unassigned_orders"] == 1
    assert default_row["products"] == [
        {"product_code": "Z93", "product_name": "BOTELLON AGUA", "quantity": 1}
    ]
    assert Decimal(default_row["total_sales"]) == Decimal(8000)

    assert (driver_row["seller_code"], driver_row["seller_name"]) == (
        99,
        "Carlos Conductor",
    )
    assert (driver_row["orders_count"], driver_row["unassigned_orders"]) == (2, 0)
    # Z91 a dos precios distintos se suma en una sola cantidad
    assert [(p["product_code"], p["quantity"]) for p in driver_row["products"]] == [
        ("Z91", 3),
        ("Z92", 1),
    ]
    assert driver_row["total_quantity"] == 4
    assert Decimal(driver_row["total_sales"]) == Decimal(14500)
    assert driver_row["exported_at"] is None


def test_sin_conductor_se_suma_a_los_pedidos_propios_del_vendedor_por_defecto(
    client, create_order, data, default_seller
):
    own = create_order(id_user_vehicle=default_seller.id_user_vehicle)  # 2 x Z91
    unassigned = create_order()  # 2 x Z91, sin conductor
    _dispatch(client, own)
    _dispatch(client, unassigned)

    (row,) = _summary(client)["sellers"]

    assert row["id_user_vehicle"] == default_seller.id_user_vehicle
    assert (row["orders_count"], row["unassigned_orders"]) == (2, 1)
    assert row["products"][0]["quantity"] == 4
    assert Decimal(row["total_sales"]) == Decimal(12000)


def test_sin_vendedor_por_defecto_responde_422_solo_si_hace_falta(
    client, create_order, data, monkeypatch
):
    monkeypatch.setattr(settings, "DEFAULT_SELLER_CODE", "98")  # no existe
    _dispatch(client, create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle))

    assert client.get(SUMMARY).status_code == 200  # todos tienen conductor

    _dispatch(client, create_order())
    response = client.get(SUMMARY)

    assert response.status_code == 422
    assert response.json()["code"] == "DEFAULT_SELLER_MISSING"


def test_resumen_de_otro_dia_y_fecha_futura(client, create_order, db, data):
    yesterday = today_bogota() - timedelta(days=1)
    order = create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle)
    _dispatch(client, order)
    _move(db, order, yesterday)

    assert _summary(client)["sellers"] == []
    assert _summary(client, yesterday)["cards"]["dispatched"] == 1

    response = client.get(f"{SUMMARY}?target_date={today_bogota() + timedelta(days=1)}")
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_CLOSURE_DATE"


def test_dia_sin_pedidos(client):
    body = _summary(client, date(2020, 1, 15))

    assert body["sellers"] == []
    assert body["exported"] is False
    assert body["cards"]["total_orders"] == 0
    assert Decimal(body["cards"]["total_income"]) == 0


def test_estado_de_exportacion_y_cambios_posteriores(client, create_order, db, data):
    driver = data.user_vehicle.id_user_vehicle
    _dispatch(client, create_order(id_user_vehicle=driver))  # 6000
    db.add(
        ShiftClosure(
            closure_date=today_bogota(),
            id_user_vehicle=driver,
            total_orders=1,
            total_sales=Decimal(6000),
            exported_siigo=True,
            exported_at=datetime.now(UTC),
        )
    )
    db.commit()

    body = _summary(client)
    assert body["exported"] is True
    assert body["sellers"][0]["exported_at"] is not None
    assert body["sellers"][0]["export_outdated"] is False

    _dispatch(client, create_order(id_user_vehicle=driver))  # llega otro pedido

    body = _summary(client)
    assert body["exported"] is False
    assert body["sellers"][0]["export_outdated"] is True


def test_codigo_de_vendedor_no_numerico_responde_422(client, create_order, db, data):
    data.user_vehicle.code = "AB"  # dato antiguo: el schema ya no lo permite
    db.commit()
    _dispatch(client, create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle))

    response = client.get(SUMMARY)

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SELLER_CODE"


def test_el_resumen_es_del_gestor_y_del_admin(admin):
    assert admin.get(SUMMARY).status_code == 200


# --- Exportación a Siigo (C3): POST /shifts_closures/{fecha}/export -----------------


def _export(client, day: date | None = None):
    return client.post(f"{URL}/{day or today_bogota()}/export")


def _sheet_rows(response) -> list[tuple]:
    assert response.status_code == 200, response.text
    sheet = load_workbook(BytesIO(response.content)).active
    return list(sheet.iter_rows(values_only=True))  # type: ignore


def _closures(db, day: date | None = None) -> dict[int, ShiftClosure]:
    return shift_closure_repository.get_by_date(db, day or today_bogota())


def test_exporta_excel_con_un_renglon_por_vendedor_producto_y_precio(
    client, create_order, data, default_seller
):
    driver = data.user_vehicle.id_user_vehicle
    p0, p1, p2 = data.products
    first = create_order(items=[item(p0, 2), item(p1, 1)], id_user_vehicle=driver)
    second = create_order(items=[item(p0, 1, "2500.00")], id_user_vehicle=driver)
    unassigned = create_order(items=[item(p2, 1)])
    _dispatch(client, first)
    _dispatch(client, second)
    _dispatch(client, unassigned, deliver=True)
    create_order(id_user_vehicle=driver)  # pendiente: no se factura

    response = _export(client)

    assert response.headers["content-type"] == MEDIA_TYPE
    assert f"cierre_{today_bogota()}.xlsx" in response.headers["content-disposition"]
    header, *rows = _sheet_rows(response)
    assert header[:3] == ("Fecha", "Cód. vendedor", "Vendedor")
    assert [r[1:] for r in rows] == [
        # vendedor por defecto (09 -> 9): el pedido sin conductor
        (9, "Hielo Foca", "Z93", "BOTELLON AGUA", 1, 8000, 8000),
        (None, "Hielo Foca", None, "Total vendedor", 1, None, 8000),
        # mismo producto a dos precios: renglones separados
        (99, "Carlos Conductor", "Z91", "BOLSA HIELO 2KG", 1, 2500, 2500),
        (99, "Carlos Conductor", "Z91", "BOLSA HIELO 2KG", 2, 3000, 6000),
        (99, "Carlos Conductor", "Z92", "BOLSA HIELO 5KG", 1, 6000, 6000),
        (None, "Carlos Conductor", None, "Total vendedor", 4, None, 14500),
        (None, None, None, "TOTAL VENTAS", 5, None, 22500),
    ]
    assert rows[0][0].date() == today_bogota()


def test_exportar_registra_los_cierres_y_el_resumen_queda_exportado(
    client, create_order, db, data, default_seller
):
    driver = data.user_vehicle.id_user_vehicle
    _dispatch(client, create_order(id_user_vehicle=driver))  # 6000
    _dispatch(client, create_order())  # 6000, sin conductor -> vendedor por defecto

    assert _export(client).status_code == 200

    closures = _closures(db)
    assert set(closures) == {driver, default_seller.id_user_vehicle}
    assert all(c.exported_siigo and c.exported_at for c in closures.values())
    assert (closures[driver].total_orders, closures[driver].total_sales) == (
        1,
        Decimal(6000),
    )
    body = _summary(client)
    assert body["exported"] is True
    assert all(row["exported_at"] for row in body["sellers"])


def test_reexportar_actualiza_el_mismo_cierre(client, create_order, db, data):
    driver = data.user_vehicle.id_user_vehicle
    _dispatch(client, create_order(id_user_vehicle=driver))
    _export(client)
    _dispatch(client, create_order(id_user_vehicle=driver))  # llega otro pedido
    assert _summary(client)["sellers"][0]["export_outdated"] is True

    assert _export(client).status_code == 200

    closures = _closures(db)
    assert len(closures) == 1
    assert (closures[driver].total_orders, closures[driver].total_sales) == (
        2,
        Decimal(12000),
    )
    assert _summary(client)["exported"] is True


def test_reexportar_quita_el_cierre_de_un_vendedor_sin_pedidos(
    client, create_order, db, data, default_seller
):
    driver = data.user_vehicle.id_user_vehicle
    order = create_order(id_user_vehicle=driver)
    _dispatch(client, order)
    _export(client)
    # se corrige el conductor después de exportar
    db.get(Order, order["id_order"]).id_user_vehicle = default_seller.id_user_vehicle
    db.commit()
    assert _summary(client)["exported"] is False

    _export(client)

    assert set(_closures(db)) == {default_seller.id_user_vehicle}
    assert _summary(client)["exported"] is True


def test_exportar_un_dia_anterior(client, create_order, db, data):
    yesterday = today_bogota() - timedelta(days=1)
    order = create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle)
    _dispatch(client, order)
    _move(db, order, yesterday)

    rows = _sheet_rows(_export(client, yesterday))

    assert rows[1][0].date() == yesterday
    assert set(_closures(db, yesterday)) == {data.user_vehicle.id_user_vehicle}
    assert _closures(db) == {}


def test_exportar_sin_pedidos_facturables_responde_422(client, create_order, db):
    create_order()  # pendiente

    response = _export(client)

    assert response.status_code == 422
    assert response.json()["code"] == "NO_BILLABLE_ORDERS"
    assert _closures(db) == {}


def test_exportar_fecha_futura_responde_422(client):
    response = _export(client, today_bogota() + timedelta(days=1))

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_CLOSURE_DATE"


def test_exportar_sin_vendedor_por_defecto_no_registra_nada(
    client, create_order, db, monkeypatch
):
    monkeypatch.setattr(settings, "DEFAULT_SELLER_CODE", "98")  # no existe
    _dispatch(client, create_order())

    response = _export(client)

    assert response.status_code == 422
    assert response.json()["code"] == "DEFAULT_SELLER_MISSING"
    assert _closures(db) == {}


# --- Cambios finales B7 (paso 1): categorías, cuadre y huella -----------------------------


def test_resumen_separa_la_factura_global_de_las_otras_ventas(
    client, create_order, data
):
    driver = data.user_vehicle.id_user_vehicle
    p0, p1, p2 = data.products
    pos_cash = create_order(items=[item(p0, 2)], id_user_vehicle=driver)  # 6000
    pos_transfer = create_order(
        items=[item(p1, 1)], id_user_vehicle=driver, payment_method="TRANSFER"
    )  # 6000
    fe_cash = create_order(
        items=[item(p2, 1)], id_user_vehicle=driver, invoice_type="ELECTRONIC"
    )  # 8000
    fe_credit = create_order(
        items=[item(p0, 1)],
        id_user_vehicle=driver,
        invoice_type="ELECTRONIC",
        payment_method="CREDIT",
    )  # 3000
    for order in (pos_cash, pos_transfer, fe_cash, fe_credit):
        _dispatch(client, order)

    body = _summary(client)

    (row,) = body["sellers"]
    # Factura global: solo el pedido POS en efectivo
    assert [(p["product_code"], p["quantity"]) for p in row["products"]] == [("Z91", 2)]
    assert row["total_quantity"] == 2
    assert Decimal(row["consolidated_total"]) == Decimal("6000")
    # Todas las ventas del vendedor
    assert (row["orders_count"], row["other_orders_count"]) == (4, 3)
    totals = {k: Decimal(v) for k, v in row["totals"].items()}
    assert totals == {
        "pos_cash": Decimal("6000"),
        "electronic_cash": Decimal("8000"),
        "pos_transfer": Decimal("6000"),
        "electronic_transfer": Decimal("0"),
        "pos_credit": Decimal("0"),
        "electronic_credit": Decimal("3000"),
    }
    assert Decimal(row["total_sales"]) == Decimal("23000")
    assert Decimal(row["cash_to_collect"]) == Decimal("14000")  # 6000 + 8000
    # Cards: los mismos totales del día
    cards = body["cards"]
    assert Decimal(cards["total_income"]) == Decimal("23000")
    assert Decimal(cards["cash_to_collect"]) == Decimal("14000")
    assert Decimal(cards["totals"]["electronic_credit"]) == Decimal("3000")


def test_cuenta_los_cancelados_despues_de_despachar(client, create_order, db):
    dispatched_then_cancelled = create_order()
    cancelled_while_pending = create_order()
    _dispatch(client, dispatched_then_cancelled)
    mark_cancelled(db, dispatched_then_cancelled["id_order"])
    mark_cancelled(db, cancelled_while_pending["id_order"])
    db.commit()

    cards = _summary(client)["cards"]

    assert cards["cancelled"] == 2
    assert cards["cancelled_after_dispatch"] == 1  # solo el que ya había salido


def test_exportar_guarda_la_huella(client, create_order, db, data):
    _dispatch(client, create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle))

    assert _export(client).status_code == 200

    closure = _closures(db)[data.user_vehicle.id_user_vehicle]
    assert closure.signature is not None and len(closure.signature) == 64


@pytest.mark.parametrize(
    "change", [{"payment_method": "TRANSFER"}, {"invoice_type": "ELECTRONIC"}]
)
def test_cambiar_pago_o_factura_tras_exportar_desactualiza_el_cierre(
    client, create_order, data, change
):
    """Con la huella se detecta aunque la cantidad de pedidos y el total no cambien."""
    order = create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle)
    _dispatch(client, order)
    _export(client)
    assert _summary(client)["exported"] is True

    patched = client.patch(f"{API}/orders/{order['id_order']}", json=change)
    assert patched.status_code == 200, patched.text

    body = _summary(client)
    assert body["sellers"][0]["export_outdated"] is True
    assert body["exported"] is False


def test_la_hoja_1_solo_lleva_pos_en_efectivo(client, create_order, data):
    driver = data.user_vehicle.id_user_vehicle
    p0, p1, _ = data.products
    _dispatch(client, create_order(items=[item(p0, 2)], id_user_vehicle=driver))
    _dispatch(
        client,
        create_order(
            items=[item(p1, 1)], id_user_vehicle=driver, payment_method="TRANSFER"
        ),
    )

    _, *rows = _sheet_rows(_export(client))

    assert [r[3] for r in rows if r[3]] == ["Z91"]  # solo el producto en efectivo
    assert rows[-1][7] == 6000  # total del día de la factura global


# --- Cambios finales B7 (paso 2): Excel de 3 hojas ---------------------------------------


def _workbook(response):
    assert response.status_code == 200, response.text
    return load_workbook(BytesIO(response.content))


def _rows(sheet) -> list[tuple]:
    return list(sheet.iter_rows(values_only=True))


@pytest.fixture()
def mixed_day(client, create_order, data, default_seller):
    """Un día con las categorías mezcladas en dos vendedores:
    - conductor 99: POS efectivo (6000), POS transferencia (6000), FE crédito (8000)
    - vendedor por defecto 09 (sin conductor): POS efectivo (3000), FE efectivo (6000)
    """
    driver = data.user_vehicle.id_user_vehicle
    p0, p1, p2 = data.products
    orders = [
        create_order(items=[item(p0, 2)], id_user_vehicle=driver),
        create_order(
            items=[item(p1, 1)], id_user_vehicle=driver, payment_method="TRANSFER"
        ),
        create_order(
            items=[item(p2, 1)],
            id_user_vehicle=driver,
            invoice_type="ELECTRONIC",
            payment_method="CREDIT",
        ),
        create_order(items=[item(p0, 1)]),
        create_order(items=[item(p1, 1)], invoice_type="ELECTRONIC"),
    ]
    for order in orders:
        _dispatch(client, order)
    return orders


def test_el_excel_tiene_las_3_hojas(client, mixed_day):
    workbook = _workbook(_export(client))

    assert workbook.sheetnames == [
        "Consolidado POS",
        "Otras facturas",
        "Cuadre de caja",
    ]


def test_hoja_otras_facturas_pedido_por_pedido(client, mixed_day):
    sheet = _workbook(_export(client))["Otras facturas"]
    header, *rows = _rows(sheet)

    assert header[3:8] == (
        "PO",
        "Tipo factura",
        "Método pago",
        "Cliente factura",
        "Cliente",
    )
    lines = [r for r in rows if r[0] is not None]  # renglones de producto
    # Vendedor 09 (FE efectivo) va antes que el 99; dentro del 99: POS transf., FE crédito
    assert [(r[1], r[4], r[5]) for r in lines] == [
        (9, "Electrónica", "Efectivo"),
        (99, "POS", "Transferencia"),
        (99, "Electrónica", "Crédito"),
    ]
    pos_transfer = lines[1]
    assert pos_transfer[6:8] == ("CUANTÍAS MENORES", "CLIENTE REGISTRADO")
    fe_credit = lines[2]
    assert fe_credit[6:8] == ("CLIENTE REGISTRADO", "CLIENTE REGISTRADO")
    assert rows[-1][9] == "TOTAL OTRAS FACTURAS"
    assert rows[-1][12] == 20000  # 6000 + 6000 + 8000


def test_cuadre_de_caja_y_cruce_entre_hojas(client, mixed_day):
    workbook = _workbook(_export(client))
    _, *consolidated = _rows(workbook["Consolidado POS"])
    _, *others = _rows(workbook["Otras facturas"])
    header, *cash = _rows(workbook["Cuadre de caja"])

    assert header == (
        "Cód. vendedor",
        "Vendedor",
        "Pedidos",
        "Efectivo POS",
        "Efectivo FE",
        "Transferencia POS",
        "Transferencia FE",
        "Crédito POS",
        "Crédito FE",
        "Total vendido",
        "Efectivo a recibir",
    )
    by_seller = {row[0]: row for row in cash[:2]}
    assert by_seller[9] == (9, "Hielo Foca", 2, 3000, 6000, 0, 0, 0, 0, 9000, 9000)
    assert by_seller[99] == (
        99,
        "Carlos Conductor",
        3,
        6000,
        0,
        6000,
        0,
        0,
        8000,
        20000,
        6000,
    )
    total = cash[2]
    assert total[1] == "TOTAL"
    assert total[2:] == (5, 9000, 6000, 6000, 0, 0, 8000, 29000, 15000)

    # Cruces: hoja 3 = hoja 1 (efectivo POS) + hoja 2 (lo demás), por vendedor
    consolidated_by_seller = {
        r[2]: r[7] for r in consolidated if r[4] == "Total vendedor"
    }
    others_by_seller = {r[2]: r[12] for r in others if r[9] == "Total vendedor"}
    for row in cash[:2]:
        name, pos_cash, sold = row[1], row[3], row[9]
        assert consolidated_by_seller.get(name, 0) == pos_cash
        assert others_by_seller.get(name, 0) == sold - pos_cash
    assert consolidated[-1][7] + others[-1][12] == total[9]


def test_cuadre_lista_los_despachados_cancelados_sin_sumarlos(
    client, create_order, db, data
):
    driver = data.user_vehicle.id_user_vehicle
    kept = create_order(id_user_vehicle=driver)  # 6000
    returned = create_order(id_user_vehicle=driver, payment_method="TRANSFER")
    for order in (kept, returned):
        _dispatch(client, order)
    cancelled = mark_cancelled(db, returned["id_order"])
    cancelled.cancel_note = "No estaba"
    cancelled.cancelled_at = datetime(2026, 11, 11, 20, 15, tzinfo=UTC)  # 15:15 Bogotá
    cancelled.id_user_canceller = data.taker.id_user
    db.commit()

    rows = _rows(_workbook(_export(client))["Cuadre de caja"])

    total = next(r for r in rows if r[1] == "TOTAL")
    assert total[9] == 6000  # el cancelado no suma
    title = rows.index(("Pedidos despachados y cancelados (no suman)",) + (None,) * 10)
    header, listed = rows[title + 1], rows[title + 2]
    assert header[:3] == ("PO", "Vendedor", "Cliente")
    assert listed[:10] == (
        returned["purchase_order"],
        "99 - Carlos Conductor",
        "CLIENTE REGISTRADO",
        "Transferencia",
        "POS",
        6000,
        "Otro",
        "No estaba",
        "Ana Gestora",
        "15:15",
    )


def test_cuadre_sin_cancelados(client, create_order, data):
    _dispatch(client, create_order(id_user_vehicle=data.user_vehicle.id_user_vehicle))

    rows = _rows(_workbook(_export(client))["Cuadre de caja"])

    assert rows[-1][0] == "Sin pedidos cancelados después del despacho"
