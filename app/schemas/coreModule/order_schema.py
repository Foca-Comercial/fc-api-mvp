from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.coreModule.order import OrderState
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


@partial_model
class OrderUpdate(OrderBase):
    pass


class OrderResponse(OrderBase):
    id_order: int
    creation_datetime: datetime
    dispatch_time: time | None
    state: OrderState

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
