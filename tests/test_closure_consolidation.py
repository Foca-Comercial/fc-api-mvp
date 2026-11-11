"""Motor del cierre (closure_consolidation.py): sin BD, solo los cálculos."""

from decimal import Decimal

from app.services.coreModule.closure_consolidation import (
    CATEGORIES,
    ClosureOrder,
    ClosureOrderLine,
    SellerClosure,
    category_of,
)
from app.utils.enums.invoice_type import InvoiceType
from app.utils.enums.order_state import OrderState
from app.utils.enums.payment_method import PaymentMethod

CASH = PaymentMethod.CASH
TRANSFER = PaymentMethod.TRANSFER
CREDIT = PaymentMethod.CREDIT
POS, FE = InvoiceType.POS, InvoiceType.ELECTRONIC


def _order(id_order, payment, invoice, *lines, unassigned=False) -> ClosureOrder:
    order = ClosureOrder(
        id_order=id_order,
        purchase_order=f"{id_order:03d}",
        state=OrderState.DISPATCHED,
        payment_method=payment,
        invoice_type=invoice,
        client_name="CLIENTE",
        unassigned=unassigned,
    )
    for id_product, quantity, price in lines:
        order.lines.append(
            ClosureOrderLine(
                id_product=id_product,
                product_code=f"{id_product:03d}",
                product_name=f"PRODUCTO {id_product}",
                quantity=quantity,
                unit_price=Decimal(price),
                subtotal=Decimal(price) * quantity,
            )
        )
    return order


def _seller(*orders) -> SellerClosure:
    return SellerClosure(1, "01", 1, "HIELO FOCA", orders=list(orders))


def test_hay_seis_categorias_una_por_combinacion():
    keys = {category_of(i, p).key for i in InvoiceType for p in PaymentMethod}
    assert keys == {c.key for c in CATEGORIES}
    assert len(CATEGORIES) == 6


def test_factura_global_separa_el_mismo_producto_por_precio():
    """El ejemplo del cliente: BULTO DE ESCARCHA a 9.000 x 20 y a 15.000 x 15."""
    seller = _seller(
        _order(1, CASH, POS, (42, 20, "9000")),
        _order(2, CASH, POS, (42, 15, "15000")),
        _order(3, CASH, POS, (42, 5, "9000.00")),  # mismo precio: se suma
    )

    lines = [
        (li.unit_price, li.quantity, li.subtotal) for li in seller.consolidated_lines
    ]

    assert lines == [
        (Decimal("9000"), 25, Decimal("225000")),
        (Decimal("15000"), 15, Decimal("225000")),
    ]
    assert seller.consolidated_quantity == 40
    assert seller.consolidated_total == Decimal("450000")
    products = seller.consolidated_products()
    assert [(p.product_code, p.quantity) for p in products] == [("042", 40)]


def test_solo_pos_efectivo_va_a_la_factura_global():
    seller = _seller(
        _order(1, CASH, POS, (1, 1, "1000")),
        _order(2, TRANSFER, POS, (1, 1, "2000")),
        _order(3, CREDIT, POS, (1, 1, "3000")),
        _order(4, CASH, FE, (1, 1, "4000")),
        _order(5, TRANSFER, FE, (1, 1, "5000")),
        _order(6, CREDIT, FE, (1, 1, "6000")),
    )

    assert seller.consolidated_total == Decimal("1000")
    assert seller.totals_by_category == {
        "pos_cash": Decimal("1000"),
        "electronic_cash": Decimal("4000"),
        "pos_transfer": Decimal("2000"),
        "electronic_transfer": Decimal("5000"),
        "pos_credit": Decimal("3000"),
        "electronic_credit": Decimal("6000"),
    }
    assert seller.total_sales == Decimal("21000")
    assert seller.cash_to_collect == Decimal("5000")  # efectivo POS + efectivo FE
    # Otras facturas: POS (transferencia, crédito) y luego FE (efectivo, transf., crédito)
    assert [o.id_order for o in seller.other_orders] == [2, 3, 4, 5, 6]


def test_pedidos_y_pedidos_sin_conductor():
    seller = _seller(
        _order(1, CASH, POS, (1, 1, "1000")),
        _order(2, TRANSFER, POS, (1, 1, "1000"), unassigned=True),
    )

    assert (seller.orders_count, seller.unassigned_orders) == (2, 1)


def test_la_huella_cambia_con_cualquier_dato_del_pedido():
    order = _order(1, CASH, POS, (1, 2, "3000"))
    seller = _seller(order)
    base = seller.signature

    order.payment_method = TRANSFER
    assert seller.signature != base
    order.payment_method = CASH

    order.invoice_type = FE
    assert seller.signature != base
    order.invoice_type = POS

    order.state = OrderState.DELIVERED
    assert seller.signature != base
    order.state = OrderState.DISPATCHED

    order.lines[0].quantity = 3
    assert seller.signature != base
    order.lines[0].quantity = 2

    assert seller.signature == base  # todo restaurado: la misma huella


def test_la_huella_no_depende_del_formato_ni_del_orden():
    first = _seller(
        _order(1, CASH, POS, (1, 2, "3000"), (2, 1, "500")),
        _order(2, CASH, POS, (1, 1, "3000")),
    )
    second = _seller(
        _order(2, CASH, POS, (1, 1, "3000.00")),
        _order(1, CASH, POS, (2, 1, "500.0"), (1, 2, "3000")),
    )

    assert first.signature == second.signature
    assert len(first.signature) == 64
