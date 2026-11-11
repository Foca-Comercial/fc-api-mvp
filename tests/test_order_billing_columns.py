"""Cambios finales B1: columnas nuevas del pedido, del cliente y del cierre.

Valida lo que deja la migración d4f6a8c2e917: valores por defecto, restricciones
de la BD y la regla única "lleva CD" (Order.has_receipt).
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.coreModule.client import Client
from app.models.coreModule.order import Order
from app.utils.enums.cancel_reason import CancelReason
from app.utils.enums.invoice_type import InvoiceType
from app.utils.enums.order_state import OrderState
from app.utils.enums.payment_method import PaymentMethod
from tests.helpers import mark_cancelled


def _expect_integrity_error(db) -> None:
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- Valores por defecto --------------------------------------------------------------


def test_pedido_nuevo_es_efectivo_pos_y_lleva_cd(create_order, db):
    order = db.get(Order, create_order()["id_order"])

    assert order.payment_method == PaymentMethod.CASH
    assert order.invoice_type == InvoiceType.POS
    assert order.has_receipt is True
    assert order.observations is None
    assert order.cancel_reason is None
    assert order.items_updated_at is None
    assert order.id_user_items_updater is None


def test_cliente_nuevo_no_requiere_factura_electronica(data):
    assert data.client.requires_electronic_invoice is False


# --- Regla "lleva CD" -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("payment", "invoice", "expected"),
    [
        (PaymentMethod.CASH, InvoiceType.POS, True),
        (PaymentMethod.TRANSFER, InvoiceType.POS, False),
        (PaymentMethod.CREDIT, InvoiceType.POS, False),
        (PaymentMethod.CASH, InvoiceType.ELECTRONIC, False),
        (PaymentMethod.TRANSFER, InvoiceType.ELECTRONIC, False),
    ],
)
def test_solo_pos_en_efectivo_lleva_cd(create_order, db, payment, invoice, expected):
    order = db.get(Order, create_order()["id_order"])
    order.payment_method = payment
    order.invoice_type = invoice
    db.commit()

    # En Python...
    assert order.has_receipt is expected
    # ...y en SQL, con la misma regla
    in_sql = db.scalar(
        select(Order.has_receipt).where(Order.id_order == order.id_order)
    )
    assert in_sql is expected


def test_has_receipt_sirve_como_filtro_sql(create_order, db):
    cash = create_order()["id_order"]
    transfer = create_order()["id_order"]
    db.get(Order, transfer).payment_method = PaymentMethod.TRANSFER
    db.commit()

    ids = set(
        db.scalars(
            select(Order.id_order).where(
                Order.id_order.in_([cash, transfer]), Order.has_receipt
            )
        )
    )

    assert ids == {cash}


# --- Restricciones de la BD -------------------------------------------------------------


def test_pedido_cancelado_sin_motivo_se_rechaza(create_order, db):
    db.get(Order, create_order()["id_order"]).state = OrderState.CANCELLED

    _expect_integrity_error(db)


def test_motivo_de_cancelacion_solo_en_pedidos_cancelados(create_order, db):
    db.get(Order, create_order()["id_order"]).cancel_reason = CancelReason.OTHER

    _expect_integrity_error(db)


def test_pedido_cancelado_con_motivo_se_guarda(create_order, db):
    order = mark_cancelled(db, create_order()["id_order"])
    db.commit()

    db.expire_all()
    assert order.state == OrderState.CANCELLED
    assert order.cancel_reason == CancelReason.OTHER


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("payment_method", "BITCOIN"),
        ("invoice_type", "TICKET"),
    ],
)
def test_valores_fuera_del_enum_se_rechazan(create_order, db, column, value):
    id_order = create_order()["id_order"]

    with pytest.raises(IntegrityError):
        db.execute(
            text(f"UPDATE sale_order SET {column} = :value WHERE id_order = :id"),
            {"value": value, "id": id_order},
        )
    db.rollback()


def test_cliente_temporal_no_puede_ser_factura_electronica(db, data):
    db.add(
        Client(
            name="CLIENTE DE PASO",
            id_neighborhood=data.neighborhood.id_neighborhood,
            is_registered=False,
            requires_electronic_invoice=True,
        )
    )

    _expect_integrity_error(db)


def test_cliente_registrado_puede_ser_factura_electronica(db, data):
    data.client.requires_electronic_invoice = True
    db.commit()

    db.expire_all()
    assert data.client.requires_electronic_invoice is True


# --- Relaciones con app_user ------------------------------------------------------------


def test_varias_fk_a_usuario_no_confunden_las_relaciones(create_order, db, data):
    """sale_order ahora tiene tres FK a app_user: User.orders sigue siendo la de
    quien tomó el pedido."""
    driver = data.user_vehicle.user_role.user  # otro usuario de la data base
    order = mark_cancelled(db, create_order()["id_order"])
    order.id_user_canceller = driver.id_user
    order.id_user_items_updater = driver.id_user
    db.commit()

    db.expire_all()
    assert order.user_taker.id_user == data.taker.id_user
    assert order.user_canceller.id_user == driver.id_user  # type: ignore
    assert order.user_items_updater.id_user == driver.id_user  # type: ignore
    assert order.id_order in {o.id_order for o in data.taker.orders}
    assert order.id_order not in {o.id_order for o in driver.orders}
