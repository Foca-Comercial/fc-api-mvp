from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.coreModule.order import OrderState
from app.schemas.coreModule.client_schema import NewClientInput
from app.schemas.coreModule.order_detail_schema import OrderDetailResponse


# Schema Base
class OrderBase(BaseModel):
    purchase_order: str = Field(
        ..., max_length=3, description="Número de orden de compra"
    )
    estimated_delivery: time | None = Field(
        None, description="Hora estimada de entrega"
    )
    order_total: Decimal | None = Field(None, ge=0, description="Total del pedido")
    id_client: int = Field(..., description="Cliente que realiza el pedido")
    id_user_vehicle: int | None = Field(None, description="Conductor/vehículo asignado")


class OrderCreate(OrderBase):
    pass


# -----------------------------------------------------
# Registro de Pedidos: Ítems y Cargas Base
# -----------------------------------------------------
class OrderItemInput(BaseModel):
    id_product: int = Field(..., description="Producto vendido")
    cant: int = Field(..., gt=0, description="Cantidad vendida")
    unit_price: Decimal = Field(..., ge=0, description="Precio Especial")


class OrderCreateBase(BaseModel):
    # Sin purchase_order: el servidor asigna el consecutivo del día.
    estimated_delivery: time | None = None
    id_user_vehicle: int | None = Field(None, description="Opcional")
    items: list[OrderItemInput] = Field(..., min_length=1)


# -----------------------------------------------------
# Registro de Pedidos: Variantes por Tipo de Cliente
# -----------------------------------------------------
class OrderCreateNewClient(OrderCreateBase):
    client: NewClientInput


class OrderCreateExistingClient(OrderCreateBase):
    id_client: int


# PATCH acotado: el único campo editable de un pedido es el conductor asignado.
# No hereda de OrderBase a propósito (purchase_order, order_total e id_client
# no deben modificarse por esta vía; los items van por sync_items).
class OrderUpdate(BaseModel):
    id_user_vehicle: int | None = Field(
        None, description="Vehículo a asignar (null para desasignar)"
    )


# -----------------------------------------------------
# Actualiacion de Pedido (Quitar, Agregar, Modificar -> Productos)
# -----------------------------------------------------
class OrderItemSync(BaseModel):
    id_order_detail: int | None = Field(None, description="Null para un producto nuevo")
    id_product: int
    cant: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class OrderItemsSyncRequest(BaseModel):
    items: list[OrderItemSync] = Field(..., min_length=1)


# -----------------------------------------------------
# Registro de Pedidos: Respuesta tras registrar un pedido
# -----------------------------------------------------
class OrderResponse(OrderBase):
    id_order: int
    id_user_taker: int
    id_route: int | None = None
    creation_datetime: datetime
    dispatch_time: time | None
    delivery_time: time | None
    state: OrderState

    model_config = ConfigDict(from_attributes=True)


class OrderWithDetailsResponse(OrderResponse):
    order_details: list[OrderDetailResponse] = []


# -----------------------------------------------------
# Schema para la Tabla Principal (Dashboard)
# -----------------------------------------------------
class OrderSummaryResponse(BaseModel):
    id_order: int
    purchase_order: str
    creation_time: str
    estimated_delivery: time | None = None
    client_name: str
    zone_name: str
    product_codes: str
    total_quantity: int
    driver_code: str | None
    driver_name: str | None
    state: str

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# Schemas para el Modal de Detalles
# -----------------------------------------------------
class OrderDetailItemModal(BaseModel):
    id_order_detail: int
    id_product: int
    product_code: str
    product_name: str
    cant: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderFullDetailResponse(BaseModel):
    id_order: int
    purchase_order: str
    creation_datetime: datetime
    estimated_delivery: time | None
    dispatch_time: time | None
    state: str
    order_total: Decimal

    # Datos del Cliente Expandidos
    client_name: str
    client_phone: str | None
    client_address: str | None
    neighborhood_name: str
    zone_name: str

    # Datos del Domiciliario (Si aplica)
    driver_code: str | None
    driver_name: str | None

    # Lista de Productos
    items: list[OrderDetailItemModal]

    model_config = ConfigDict(from_attributes=True)
