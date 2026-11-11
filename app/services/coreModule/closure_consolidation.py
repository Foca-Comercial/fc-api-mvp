"""Motor del cierre de turno: clasifica y consolida los pedidos de un vendedor.

No toca la BD: recibe los pedidos facturables del día (con sus renglones) ya
asignados a cada vendedor y calcula todo lo que el cierre necesita a partir de
esos MISMOS objetos, para que el resumen, las 3 hojas del Excel y la huella
cuadren siempre entre sí:

- Consolidado (factura global en Siigo): solo POS + efectivo, un renglón por
  producto + precio (el mismo producto a dos precios queda en dos renglones).
- Otras facturas: POS con transferencia o crédito y todas las electrónicas,
  pedido por pedido.
- Cuadre: total por categoría (tipo de factura x método de pago) y efectivo a
  recibir (POS efectivo + FE efectivo).
- Huella: SHA-256 de los pedidos del vendedor; cualquier cambio posterior
  (estado, pago, factura, productos, cantidades, precios o vendedor) la altera.
"""

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal

from app.utils.enums.invoice_type import InvoiceType
from app.utils.enums.order_state import OrderState
from app.utils.enums.payment_method import PaymentMethod


@dataclass(frozen=True)
class Category:
    key: str
    invoice_type: InvoiceType
    payment_method: PaymentMethod
    label: str


# Orden fijo de las columnas del cuadre de caja
CATEGORIES: tuple[Category, ...] = (
    Category("pos_cash", InvoiceType.POS, PaymentMethod.CASH, "Efectivo POS"),
    Category(
        "electronic_cash", InvoiceType.ELECTRONIC, PaymentMethod.CASH, "Efectivo FE"
    ),
    Category(
        "pos_transfer", InvoiceType.POS, PaymentMethod.TRANSFER, "Transferencia POS"
    ),
    Category(
        "electronic_transfer",
        InvoiceType.ELECTRONIC,
        PaymentMethod.TRANSFER,
        "Transferencia FE",
    ),
    Category("pos_credit", InvoiceType.POS, PaymentMethod.CREDIT, "Crédito POS"),
    Category(
        "electronic_credit", InvoiceType.ELECTRONIC, PaymentMethod.CREDIT, "Crédito FE"
    ),
)
_BY_TYPES = {(c.invoice_type, c.payment_method): c for c in CATEGORIES}
# Orden de la hoja "Otras facturas": primero POS (transferencia, crédito), luego FE
_OTHER_POSITION = {
    "pos_transfer": 0,
    "pos_credit": 1,
    "electronic_cash": 2,
    "electronic_transfer": 3,
    "electronic_credit": 4,
}

CONSOLIDATED = "pos_cash"  # lo que va a la factura global
CASH_CATEGORIES = ("pos_cash", "electronic_cash")  # efectivo que entrega el domiciliario


def category_of(invoice_type: InvoiceType, payment_method: PaymentMethod) -> Category:
    return _BY_TYPES[(invoice_type, payment_method)]


def _money(value: Decimal) -> str:
    """Decimal normalizado a 2 decimales (3000 y 3000.00 dan la misma huella)."""
    return f"{Decimal(value):.2f}"


# ---------------------------------------------------------------------------
# Pedido
# ---------------------------------------------------------------------------
@dataclass
class ClosureOrderLine:
    id_product: int
    product_code: str
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


@dataclass
class ClosureOrder:
    id_order: int
    purchase_order: str
    state: OrderState
    payment_method: PaymentMethod
    invoice_type: InvoiceType
    client_name: str
    unassigned: bool  # sin conductor: sumado al vendedor por defecto
    lines: list[ClosureOrderLine] = field(default_factory=list)

    @property
    def category(self) -> Category:
        return category_of(self.invoice_type, self.payment_method)

    @property
    def total(self) -> Decimal:
        # Suma de los renglones (lo que se factura), no order_total
        return sum((line.subtotal for line in self.lines), Decimal(0))

    @property
    def quantity(self) -> int:
        return sum(line.quantity for line in self.lines)

    def fingerprint(self) -> str:
        lines = ";".join(
            sorted(
                f"{li.id_product}:{li.quantity}:{_money(li.unit_price)}"
                for li in self.lines
            )
        )
        return "|".join(
            (
                str(self.id_order),
                self.state.value,
                self.payment_method.value,
                self.invoice_type.value,
                _money(self.total),
                lines,
            )
        )


# ---------------------------------------------------------------------------
# Vendedor
# ---------------------------------------------------------------------------
@dataclass
class ClosureLine:
    """Renglón de la factura global: un producto a un precio."""

    id_product: int
    product_code: str
    product_name: str
    unit_price: Decimal
    quantity: int = 0
    subtotal: Decimal = Decimal(0)


@dataclass
class ConsolidatedProduct:
    product_code: str
    product_name: str
    quantity: int


@dataclass
class SellerClosure:
    """Cierre de un vendedor en un día."""

    id_user_vehicle: int
    code: str
    seller_code: int  # para Siigo: "01" -> 1
    seller_name: str
    orders: list[ClosureOrder] = field(default_factory=list)

    # --- Pedidos ---------------------------------------------------------------
    @property
    def orders_count(self) -> int:
        return len(self.orders)

    @property
    def unassigned_orders(self) -> int:
        return sum(1 for o in self.orders if o.unassigned)

    @property
    def other_orders(self) -> list[ClosureOrder]:
        """Pedidos que no van a la factura global, por categoría y PO."""
        return sorted(
            (o for o in self.orders if o.category.key != CONSOLIDATED),
            key=lambda o: (
                _OTHER_POSITION[o.category.key],
                o.purchase_order,
                o.id_order,
            ),
        )

    # --- Factura global (POS + efectivo) ---------------------------------------
    @property
    def consolidated_lines(self) -> list[ClosureLine]:
        merged: dict[tuple[int, str], ClosureLine] = {}
        for order in self.orders:
            if order.category.key != CONSOLIDATED:
                continue
            for li in order.lines:
                key = (li.id_product, _money(li.unit_price))
                line = merged.get(key)
                if line is None:
                    line = merged[key] = ClosureLine(
                        id_product=li.id_product,
                        product_code=li.product_code,
                        product_name=li.product_name,
                        unit_price=li.unit_price,
                    )
                line.quantity += li.quantity
                line.subtotal += li.subtotal
        return sorted(merged.values(), key=lambda li: (li.product_code, li.unit_price))

    @property
    def consolidated_quantity(self) -> int:
        return sum(li.quantity for li in self.consolidated_lines)

    @property
    def consolidated_total(self) -> Decimal:
        return self.totals_by_category[CONSOLIDATED]

    def consolidated_products(self) -> list[ConsolidatedProduct]:
        """Unidades de la factura global por producto, sumando sus precios."""
        by_code: dict[str, ConsolidatedProduct] = {}
        for li in self.consolidated_lines:
            product = by_code.setdefault(
                li.product_code,
                ConsolidatedProduct(li.product_code, li.product_name, 0),
            )
            product.quantity += li.quantity
        return list(by_code.values())

    # --- Cuadre -------------------------------------------------------------
    @property
    def totals_by_category(self) -> dict[str, Decimal]:
        totals = {c.key: Decimal(0) for c in CATEGORIES}
        for order in self.orders:
            totals[order.category.key] += order.total
        return totals

    @property
    def total_sales(self) -> Decimal:
        return sum(self.totals_by_category.values(), Decimal(0))

    @property
    def cash_to_collect(self) -> Decimal:
        totals = self.totals_by_category
        return sum((totals[key] for key in CASH_CATEGORIES), Decimal(0))

    # --- Huella -------------------------------------------------------------
    @property
    def signature(self) -> str:
        payload = "\n".join(sorted(o.fingerprint() for o in self.orders))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
