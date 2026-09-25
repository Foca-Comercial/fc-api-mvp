from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.utils import partial_model


# Schema Base
class SpecialCustomerPriceBase(BaseModel):
    id_client: int = Field(..., description="Cliente al que aplica el precio especial")
    id_product: int = Field(..., description="Producto con precio especial")
    agreed_price: Decimal = Field(
        ..., ge=0, description="Precio acordado con el cliente"
    )


class SpecialCustomerPriceCreate(SpecialCustomerPriceBase):
    pass


@partial_model
class SpecialCustomerPriceUpdate(SpecialCustomerPriceBase):
    pass


class SpecialCustomerPriceResponse(SpecialCustomerPriceBase):
    id_client_price: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
