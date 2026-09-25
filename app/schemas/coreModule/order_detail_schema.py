from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.utils import partial_model


# Schemba
class OrderDetailBase(BaseModel):
    id_order: int = Field(..., description="Pedido al que pertenece el detalle")
    id_product: int = Field(..., description="Producto vendido")
    cant: int = Field(..., gt=0, description="Cantidad vendida")
    unit_price: Decimal = Field(..., ge=0, description="Precio unitario aplicado")
    subtotal: Decimal = Field(..., ge=0, description="Subtotal (cant × unit_price)")


class OrderDetailCreate(OrderDetailBase):
    pass


@partial_model
class OrderDetailUpdate(OrderDetailBase):
    pass


class OrderDetailResponse(OrderDetailBase):
    id_order_detail: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
