"""Pedidos por ruta: rutas del día, precarga y creación en lote."""

from datetime import time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.coreModule.order_schema import OrderResponse

# Cantidad con la que se precarga cada producto en el formulario de la ruta
DEFAULT_ROUTE_CANT = 1


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
    unit_price: Decimal = Field(..., description="Precio especial pactado con el cliente")
    cant: int = Field(
        DEFAULT_ROUTE_CANT, description="Cantidad sugerida; el gestor la edita"
    )


class RouteTemplateClient(BaseModel):
    id_client: int
    name: str
    phone: str | None
    address: str | None
    neighborhood_name: str
    zone_name: str
    products: list[RouteTemplateProduct] = Field(
        ...,
        description="Productos con precio especial. Vacío si el cliente no tiene "
        "precios especiales: no se le puede generar pedido desde la ruta",
    )
    existing_order_id: int | None = Field(
        None, description="Pedido de hoy ya generado desde esta ruta para el cliente"
    )


class RouteOrderTemplateResponse(BaseModel):
    id_route: int
    name: str
    departure_time: time
    clients: list[RouteTemplateClient]


# -----------------------------------------------------
# Creación en lote
# -----------------------------------------------------
class RouteOrderItemInput(BaseModel):
    # Sin precio: el backend usa el precio especial pactado del cliente
    id_product: int = Field(..., gt=0, description="Producto con precio especial")
    cant: int = Field(..., gt=0, description="Cantidad")


class RouteOrderClientInput(BaseModel):
    id_client: int = Field(..., gt=0, description="Cliente de la ruta (ver /template)")
    items: list[RouteOrderItemInput] = Field(..., min_length=1)


class RouteOrdersCreate(BaseModel):
    estimated_delivery: time | None = Field(
        None, description="Hora estimada de entrega para todos los pedidos"
    )
    id_user_vehicle: int | None = Field(
        None, gt=0, description="Conductor asignado a todos los pedidos (opcional)"
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
