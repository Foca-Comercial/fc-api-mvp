from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.coreModule.order import OrderState
from app.schemas.coreModule.client_schema import NewClientInput
from app.schemas.coreModule.order_detail_schema import OrderDetailResponse
from app.utils.helpers.schema_helper import partial_model


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


# Un producto dentro del pedido
class OrderItemInput(BaseModel):
    id_product: int = Field(..., description="Producto vendido")
    cant: int = Field(..., gt=0, description="Cantidad vendida")
    unit_price: Decimal = Field(..., ge=0, description="Precio Especial")


class OrderCreateBase(BaseModel):
    purchase_order: str = Field(..., max_length=3)
    estimated_delivery: time | None = None
    id_user_vehicle: int | None = Field(None, description="Opcional")
    items: list[OrderItemInput] = Field(..., min_length=1)


class OrderCreateNewClient(OrderCreateBase):
    client: NewClientInput


class OrderCreateExistingClient(OrderCreateBase):
    id_client: int


@partial_model
class OrderUpdate(OrderBase):
    pass


class OrderResponse(OrderBase):
    id_order: int
    id_user_taker: int
    creation_datetime: datetime
    dispatch_time: time | None
    state: OrderState

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )


class OrderWithDetailsResponse(OrderResponse):
    order_details: list[OrderDetailResponse] = []
