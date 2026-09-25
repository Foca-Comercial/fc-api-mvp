from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.utils import partial_model


# Schema Base
class ProductBase(BaseModel):
    code: str = Field(
        ..., min_length=3, max_length=3, description="Código único del producto"
    )
    name: str = Field(..., max_length=50)
    description: str | None = Field(None, max_length=200)
    base_price: Decimal = Field(..., ge=0, description="Precio base del producto")
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
