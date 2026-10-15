"""Pedidos por ruta: rutas del día, precarga y creación en lote."""

from datetime import time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.coreModule.order_schema import OrderItemInput, OrderResponse


# -----------------------------------------------------
# Rutas habilitadas para un día
# -----------------------------------------------------
class RouteOfDayResponse(BaseModel):
    id_route: int
    name: str
    departure_time: time
    days_week: list[int]
    clients_count: int = Field(..., description="Clientes activos y registrados en la ruta")
    orders_count: int = Field(
        ..., description="Pedidos ya generados ese día desde la ruta (sin cancelados)"
    )


# -----------------------------------------------------
# Precarga del formulario de una ruta
# -----------------------------------------------------
class RouteTemplateProduct(BaseModel):
    id_product: int
    code: str
    name: str
    base_price: Decimal


class RouteTemplatePrice(BaseModel):
    id_product: int
    unit_price: Decimal = Field(..., description="Precio especial si existe, si no el base")
    is_special: bool


class RouteTemplateClient(BaseModel):
    id_client: int
    name: str
    phone: str | None
    address: str | None
    neighborhood_name: str
    zone_name: str
    prices: list[RouteTemplatePrice]
    existing_order_id: int | None = Field(
        None, description="Pedido de hoy ya generado desde esta ruta para el cliente"
    )


class RouteOrderTemplateResponse(BaseModel):
    id_route: int
    name: str
    departure_time: time
    products: list[RouteTemplateProduct]
    clients: list[RouteTemplateClient]


# -----------------------------------------------------
# Creación en lote
# -----------------------------------------------------
class RouteOrderClientInput(BaseModel):
    id_client: int
    items: list[OrderItemInput] = Field(..., min_length=1)


class RouteOrdersCreate(BaseModel):
    estimated_delivery: time | None = Field(
        None, description="Hora estimada de entrega para todos los pedidos"
    )
    id_user_vehicle: int | None = Field(
        None, description="Conductor asignado a todos los pedidos (opcional)"
    )
    orders: list[RouteOrderClientInput] = Field(
        ...,
        min_length=1,
        description="Solo los clientes con productos; los demás se omiten",
    )


class RouteOrdersCreatedResponse(BaseModel):
    id_route: int
    created: int
    orders: list[OrderResponse]
