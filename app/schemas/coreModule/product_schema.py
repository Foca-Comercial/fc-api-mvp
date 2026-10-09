from decimal import Decimal

from pydantic import BaseModel, Field

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText


# Schema Base
class ProductBase(BaseModel):
    code: UpperText = Field(
        ...,
        max_length=3,
        pattern=r"^[0-9]{3}$",
        description="Código de 3 dígitos",
    )
    name: UpperText = Field(..., max_length=50)
    description: UpperText | None = Field(None, max_length=200)
    base_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    active: bool = True


class ProductCreate(ProductBase):
    pass


@partial_model
class ProductUpdate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id_product: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )


# -----------------------------------------------------
# Catalogo de productos
# -----------------------------------------------------
class ProductCatalogItem(BaseModel):
    id_product: int
    code: str
    name: str
    base_price: Decimal
    agreed_price: Decimal | None = None
    effective_price: Decimal = Field(
        ..., description="agreed_price si existe, si no base_price"
    )
