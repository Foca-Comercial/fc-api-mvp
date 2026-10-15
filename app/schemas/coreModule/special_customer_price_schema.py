from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.utils.helpers.schema_helper import partial_model


# Schema Base
class SpecialCustomerPriceBase(BaseModel):
    id_client: int = Field(..., gt=0, description="Cliente con precio especial")
    id_product: int = Field(..., gt=0, description="Producto con precio especial")
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

    model_config = ConfigDict(from_attributes=True)
