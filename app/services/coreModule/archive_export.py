"""Convierte las filas de pedidos del mes en la tabla que se escribe en Sheets."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.utils.enums.order_state import OrderState

STATE_LABELS = {
    OrderState.PENDING: "Pendiente",
    OrderState.DISPATCHED: "Despachado",
    OrderState.DELIVERED: "Entregado",
    OrderState.CANCELLED: "Cancelado",
}

HEADER = (
    "Fecha",
    "Hora",
    "N.° pedido",
    "Cliente",
    "Teléfono",
    "Barrio",
    "Zona",
    "Ruta",
    "Conductor",
    "Tomado por",
    "Estado",
    "Hora despacho",
    "Hora entrega",
    "Código",
    "Producto",
    "Cantidad",
    "Precio unit.",
    "Subtotal",
    "Total pedido",
)
# Índices (desde 0) de las columnas con formato de moneda
MONEY_COLUMNS = (16, 17, 18)


@dataclass(frozen=True)
class ExportTable:
    header: tuple[str, ...]
    rows: list[list[Any]]
    orders_count: int
    total_sales: Decimal  # sin pedidos cancelados


def _money(value: Decimal | None) -> float | str:
    # Sheets recibe números (no texto) para poder sumar y filtrar
    return float(value) if value is not None else ""


def _hhmm(value) -> str:
    return value.strftime("%H:%M") if value is not None else ""


def _driver(row) -> str:
    if row.driver_code is None:
        return ""
    return f"{row.driver_code} - {row.driver_name}" if row.driver_name else row.driver_code


def build_export_table(rows: list) -> ExportTable:
    table: list[list[Any]] = []
    order_totals: dict[int, Decimal] = {}
    for row in rows:
        table.append(
            [
                row.order_date.isoformat(),
                row.creation_time,
                row.purchase_order,
                row.client_name,
                row.client_phone or "",
                row.neighborhood_name,
                row.zone_name,
                row.route_name or "",
                _driver(row),
                row.taker_name,
                STATE_LABELS[row.state],
                _hhmm(row.dispatch_time),
                _hhmm(row.delivery_time),
                row.product_code,
                row.product_name,
                row.cant,
                _money(row.unit_price),
                _money(row.subtotal),
                _money(row.order_total),
            ]
        )
        if row.state != OrderState.CANCELLED:
            order_totals[row.id_order] = row.order_total or Decimal(0)

    return ExportTable(
        header=HEADER,
        rows=table,
        orders_count=len({row.id_order for row in rows}),
        total_sales=sum(order_totals.values(), Decimal(0)),
    )
