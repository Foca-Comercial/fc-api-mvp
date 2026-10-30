from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

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

    model_config = ConfigDict(from_attributes=True)


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


# -----------------------------------------------------
# Panel de administración (/products/admin)
# -----------------------------------------------------
@dataclass(frozen=True)
class ProductAdminFilters:
    """Filtros del listado de administración (ya validados por el router)."""

    search: str | None = None  # código (empieza por) o nombre (contiene)
    active: bool | None = None  # None = activos e inactivos


class ProductAdminRow(BaseModel):
    id_product: int
    code: str
    name: str
    description: str | None
    base_price: Decimal
    active: bool
    special_prices_count: int = Field(
        ..., description="Clientes con precio especial pactado para el producto"
    )
    in_use: bool = Field(
        ...,
        description="Tiene pedidos: su código ya no se puede cambiar (lo usan el "
        "cierre, Siigo y el archivado)",
    )

    model_config = ConfigDict(from_attributes=True)
