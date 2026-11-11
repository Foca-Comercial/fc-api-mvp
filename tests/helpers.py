"""Utilidades compartidas por los tests."""

from app.models.coreModule.order import Order
from app.models.coreModule.product import Product
from app.utils.enums.cancel_reason import CancelReason
from app.utils.enums.order_state import OrderState

API = "/api/v1"


def item(product: Product, cant: int, unit_price: str | None = None) -> dict:
    """Renglón de pedido; por defecto usa el precio base del producto."""
    return {
        "id_product": product.id_product,
        "cant": cant,
        "unit_price": unit_price or str(product.base_price),
    }


def mark_cancelled(db, id_order: int) -> Order:
    """Cancela un pedido directo en la BD (sin commit). Todo pedido cancelado
    lleva motivo: lo exige chk_order_cancel_reason."""
    order = db.get(Order, id_order)
    order.state = OrderState.CANCELLED
    order.cancel_reason = CancelReason.OTHER
    return order


class FakeSheetsWriter:
    """Escritor de Google Sheets en memoria (no se conecta a Google)."""

    def __init__(self) -> None:
        self.sheets: dict[tuple[str, str], dict] = {}
        self.calls = 0
        self.fail: Exception | None = None
        self.lose_rows = 0  # simula filas que no quedaron escritas

    def write_sheet(self, spreadsheet_id, title, header, rows, money_columns=()):
        self.calls += 1
        if self.fail:
            raise self.fail
        self.sheets[(spreadsheet_id, title)] = {
            "header": list(header),
            "rows": [list(r) for r in rows],
            "money_columns": list(money_columns),
        }
        return len(rows) - self.lose_rows
