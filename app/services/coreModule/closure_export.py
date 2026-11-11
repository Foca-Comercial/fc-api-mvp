"""Excel (.xlsx) del cierre de turno: 3 hojas para facturar y cuadrar caja.

1. "Consolidado POS": factura global por vendedor en Siigo. Solo POS + efectivo,
   un renglón por producto + precio (el mismo producto a dos precios queda en dos
   renglones), total por vendedor y total de ventas.
2. "Otras facturas": lo que se factura aparte en Siigo, pedido por pedido: POS
   con transferencia o crédito y todas las facturas electrónicas.
3. "Cuadre de caja": por vendedor, ventas por tipo de factura y método de pago,
   y el efectivo a recibir. Debajo, los pedidos despachados y luego cancelados
   (informativo, no suman).

Todo sale de los mismos objetos de closure_consolidation.py, así que las hojas
cuadran entre sí: el efectivo POS de la hoja 3 es el total de la hoja 1 y las
demás columnas son los pedidos de la hoja 2. No depende de la BD.
"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.coreModule.closure_consolidation import (
    CANCEL_REASON_LABELS,
    CATEGORIES,
    INVOICE_LABELS,
    PAYMENT_LABELS,
    CancelledOrder,
    SellerClosure,
)

MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

SHEET_CONSOLIDATED = "Consolidado POS"
SHEET_OTHERS = "Otras facturas"
SHEET_CASH = "Cuadre de caja"

CONSOLIDATED_HEADER = (
    "Fecha",
    "Cód. vendedor",
    "Vendedor",
    "Cód. producto",
    "Producto",
    "Cantidad",
    "Precio unit.",
    "Subtotal",
)
OTHERS_HEADER = (
    "Fecha",
    "Cód. vendedor",
    "Vendedor",
    "PO",
    "Tipo factura",
    "Método pago",
    "Cliente factura",
    "Cliente",
    "Cód. producto",
    "Producto",
    "Cantidad",
    "Precio unit.",
    "Subtotal",
)
CASH_HEADER = (
    "Cód. vendedor",
    "Vendedor",
    "Pedidos",
    *(c.label for c in CATEGORIES),
    "Total vendido",
    "Efectivo a recibir",
)
CANCELLED_HEADER = (
    "PO",
    "Vendedor",
    "Cliente",
    "Método pago",
    "Tipo factura",
    "Total",
    "Motivo",
    "Observación",
    "Canceló",
    "Hora",
)

DATE_FORMAT = "DD/MM/YYYY"
QTY_FORMAT = "#,##0"
MONEY_FORMAT = '"$"#,##0.00'

_BOLD = Font(bold=True)
_TITLE_FONT = Font(bold=True, size=12)
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
_ORDER_FILL = PatternFill("solid", fgColor="F2F2F2")
_TOTAL_FILL = PatternFill("solid", fgColor="DDEBF7")
_GRAND_FILL = PatternFill("solid", fgColor="BDD7EE")
_TOP_BORDER = Border(top=Side(style="thin"))


def filename_for(day: date) -> str:
    return f"cierre_{day.isoformat()}.xlsx"


def build_closure_workbook(
    day: date,
    sellers: Sequence[SellerClosure],
    cancelled: Sequence[CancelledOrder] = (),
) -> bytes:
    wb = Workbook()
    _consolidated_sheet(wb.active, day, sellers)  # type: ignore[arg-type]
    _others_sheet(wb.create_sheet(SHEET_OTHERS), day, sellers)
    _cash_sheet(wb.create_sheet(SHEET_CASH), sellers, cancelled)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Hoja 1: factura global (POS + efectivo)
# ---------------------------------------------------------------------------
def _consolidated_sheet(
    ws: Worksheet, day: date, sellers: Sequence[SellerClosure]
) -> None:
    ws.title = SHEET_CONSOLIDATED
    _header(ws, CONSOLIDATED_HEADER)
    money, qty = (7, 8), (6,)

    # Un vendedor sin ventas POS en efectivo no tiene factura global
    consolidated = [s for s in sellers if s.consolidated_lines]
    for seller in consolidated:
        for line in seller.consolidated_lines:
            ws.append(
                (
                    day,
                    seller.seller_code,  # número: Siigo recibe 1, no "01"
                    seller.seller_name,
                    line.product_code,
                    line.product_name,
                    line.quantity,
                    line.unit_price,
                    line.subtotal,
                )
            )
            _formats(ws, money=money, qty=qty, date_col=1)
        ws.append(
            (
                None,
                None,
                seller.seller_name,
                None,
                "Total vendedor",
                seller.consolidated_quantity,
                None,
                seller.consolidated_total,
            )
        )
        _total_row(ws, _TOTAL_FILL, money=money, qty=qty)

    ws.append(
        (
            None,
            None,
            None,
            None,
            "TOTAL VENTAS",
            sum(s.consolidated_quantity for s in consolidated),
            None,
            sum((s.consolidated_total for s in consolidated), Decimal(0)),
        )
    )
    _total_row(ws, _GRAND_FILL, money=money, qty=qty)
    _widths(ws, (12, 14, 28, 14, 30, 11, 14, 16))


# ---------------------------------------------------------------------------
# Hoja 2: otras facturas, pedido por pedido
# ---------------------------------------------------------------------------
def _others_sheet(ws: Worksheet, day: date, sellers: Sequence[SellerClosure]) -> None:
    _header(ws, OTHERS_HEADER)
    money, qty = (12, 13), (11,)

    grand_total = Decimal(0)
    for seller in sellers:
        orders = seller.other_orders
        if not orders:
            continue
        seller_total = Decimal(0)
        for order in orders:
            for line in order.lines:
                ws.append(
                    (
                        day,
                        seller.seller_code,
                        seller.seller_name,
                        order.purchase_order,
                        INVOICE_LABELS[order.invoice_type],
                        PAYMENT_LABELS[order.payment_method],
                        order.invoice_client,
                        order.client_name,
                        line.product_code,
                        line.product_name,
                        line.quantity,
                        line.unit_price,
                        line.subtotal,
                    )
                )
                _formats(ws, money=money, qty=qty, date_col=1)
            ws.append(
                (
                    None,
                    None,
                    seller.seller_name,
                    order.purchase_order,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "Total pedido",
                    order.quantity,
                    None,
                    order.total,
                )
            )
            _total_row(ws, _ORDER_FILL, money=money, qty=qty)
            seller_total += order.total
        ws.append(
            (
                None,
                None,
                seller.seller_name,
                None,
                None,
                None,
                None,
                None,
                None,
                "Total vendedor",
                None,
                None,
                seller_total,
            )
        )
        _total_row(ws, _TOTAL_FILL, money=money, qty=qty)
        grand_total += seller_total

    ws.append((*([None] * 9), "TOTAL OTRAS FACTURAS", None, None, grand_total))
    _total_row(ws, _GRAND_FILL, money=money, qty=qty)
    _widths(ws, (12, 14, 26, 8, 13, 15, 22, 26, 14, 28, 11, 14, 16))


# ---------------------------------------------------------------------------
# Hoja 3: cuadre de caja + despachados cancelados
# ---------------------------------------------------------------------------
def _cash_sheet(
    ws: Worksheet,
    sellers: Sequence[SellerClosure],
    cancelled: Sequence[CancelledOrder],
) -> None:
    _header(ws, CASH_HEADER)
    first_money = 4  # columnas de dinero: las 6 categorías + total + efectivo
    money = tuple(range(first_money, len(CASH_HEADER) + 1))
    qty = (3,)

    for seller in sellers:
        totals = seller.totals_by_category
        ws.append(
            (
                seller.seller_code,
                seller.seller_name,
                seller.orders_count,
                *(totals[c.key] for c in CATEGORIES),
                seller.total_sales,
                seller.cash_to_collect,
            )
        )
        _formats(ws, money=money, qty=qty)

    ws.append(
        (
            None,
            "TOTAL",
            sum(s.orders_count for s in sellers),
            *(
                sum((s.totals_by_category[c.key] for s in sellers), Decimal(0))
                for c in CATEGORIES
            ),
            sum((s.total_sales for s in sellers), Decimal(0)),
            sum((s.cash_to_collect for s in sellers), Decimal(0)),
        )
    )
    _total_row(ws, _GRAND_FILL, money=money, qty=qty)

    # Despachados y luego cancelados: informativo, no suma en el cuadre
    ws.append(())
    ws.append(("Pedidos despachados y cancelados (no suman)",))
    ws.cell(ws.max_row, 1).font = _TITLE_FONT
    _header(ws, CANCELLED_HEADER, row=ws.max_row + 1)
    if not cancelled:
        ws.append(("Sin pedidos cancelados después del despacho",))
    for order in cancelled:
        ws.append(
            (
                order.purchase_order,
                order.seller,
                order.client_name,
                PAYMENT_LABELS[order.payment_method],
                INVOICE_LABELS[order.invoice_type],
                order.total,
                CANCEL_REASON_LABELS[order.cancel_reason],
                order.cancel_note,
                order.canceller_name,
                order.cancelled_at.strftime("%H:%M") if order.cancelled_at else None,
            )
        )
        _formats(ws, money=(6,))

    _widths(ws, (14, 28, 22, 16, 16, 18, 18, 14, 14, 16, 18))


# ---------------------------------------------------------------------------
# Formato
# ---------------------------------------------------------------------------
def _header(ws: Worksheet, titles: Sequence[str], row: int = 1) -> None:
    for col, title in enumerate(titles, start=1):
        cell = ws.cell(row, col, title)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
    if row == 1:
        ws.freeze_panes = "A2"


def _formats(
    ws: Worksheet,
    *,
    money: Sequence[int] = (),
    qty: Sequence[int] = (),
    date_col: int | None = None,
) -> None:
    row = ws.max_row
    if date_col is not None:
        ws.cell(row, date_col).number_format = DATE_FORMAT
    for col in qty:
        ws.cell(row, col).number_format = QTY_FORMAT
    for col in money:
        ws.cell(row, col).number_format = MONEY_FORMAT


def _total_row(
    ws: Worksheet, fill: PatternFill, *, money: Sequence[int], qty: Sequence[int]
) -> None:
    _formats(ws, money=money, qty=qty)
    for cell in ws[ws.max_row]:
        cell.font = _BOLD
        cell.fill = fill
        cell.border = _TOP_BORDER


def _widths(ws: Worksheet, widths: Sequence[int]) -> None:
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width
