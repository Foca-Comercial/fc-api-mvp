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


# -----------------------------------------------------
# Panel de administración: precios especiales de un cliente registrado
# (/clients/admin/{id}/special-prices). Una fila por producto (único por cliente).
# -----------------------------------------------------
class ClientSpecialPriceSet(BaseModel):
    agreed_price: Decimal = Field(
        ...,
        ge=0,
        max_digits=12,
        decimal_places=2,
        description="Precio pactado con el cliente para el producto",
    )


class ClientSpecialPriceRow(BaseModel):
    id_product: int
    product_code: str
    product_name: str
    product_active: bool = Field(
        ..., description="Un producto inactivo no se ofrece en los pedidos"
    )
    base_price: Decimal
    agreed_price: Decimal

    model_config = ConfigDict(from_attributes=True)
