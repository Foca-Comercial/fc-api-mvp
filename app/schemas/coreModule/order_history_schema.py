"""Vista Histórico: listado paginado de pedidos con filtros y totales."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.utils.enums.order_state import OrderState


@dataclass(frozen=True)
class OrderHistoryFilters:
    """Filtros ya resueltos (fechas por defecto aplicadas) que recibe el repositorio."""

    date_from: date
    date_to: date
    state: OrderState | None = None
    id_route: int | None = None
    id_user_vehicle: int | None = None
    search: str | None = None


class OrderHistoryRow(BaseModel):
    id_order: int
    purchase_order: str
    order_date: date = Field(..., description="Día de entrega (Bogotá)")
    creation_time: str = Field(..., description="Hora de creación HH:MM (Bogotá)")
    client_name: str
    zone_name: str
    route_name: str | None
    product_codes: str
    total_quantity: int
    order_total: Decimal | None
    driver_code: str | None
    driver_name: str | None
    state: OrderState


class OrderHistoryPage(BaseModel):
    date_from: date
    date_to: date
    page: int
    page_size: int
    total: int = Field(..., description="Pedidos que cumplen el filtro")
    pages: int
    total_sales: Decimal = Field(
        ..., description="Suma de order_total del filtro, sin pedidos cancelados"
    )
    items: list[OrderHistoryRow]
