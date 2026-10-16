from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.utils.helpers.schema_helper import partial_model


# Schema Base
class ShiftClosureBase(BaseModel):
    closure_date: date = Field(..., description="Fecha del cierre de turno")
    id_user_vehicle: int = Field(
        ..., description="Conductor/vehículo del turno cerrado"
    )
    total_orders: int = Field(..., ge=0, description="Cantidad de pedidos del turno")
    total_sales: Decimal = Field(..., ge=0, description="Total vendido en el turno")
    exported_siigo: bool = False


class ShiftClosureCreate(ShiftClosureBase):
    pass


@partial_model
class ShiftClosureUpdate(ShiftClosureBase):
    pass


class ShiftClosureResponse(ShiftClosureBase):
    id_shift_closure: int
    exported_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# Vista Cierre: resumen del día
# -----------------------------------------------------
class ClosureProduct(BaseModel):
    product_code: str
    product_name: str
    quantity: int = Field(
        ..., description="Unidades del día, sumando todos los precios"
    )


class ClosureSellerRow(BaseModel):
    id_user_vehicle: int
    seller_code: int = Field(
        ..., description="Código del vendedor sin ceros a la izquierda (Siigo)"
    )
    seller_name: str
    products: list[ClosureProduct]
    total_quantity: int
    orders_count: int
    unassigned_orders: int = Field(
        0,
        description="Pedidos sin conductor sumados a este vendedor (solo el de "
        "por defecto)",
    )
    total_sales: Decimal
    exported_at: datetime | None = Field(
        None, description="Última exportación a Siigo de este vendedor y día"
    )
    export_outdated: bool = Field(
        False,
        description="Se exportó, pero los pedidos o el total cambiaron después",
    )


class ClosureCards(BaseModel):
    total_orders: int = Field(..., description="Pedidos del día en cualquier estado")
    pending: int
    dispatched: int
    delivered: int
    cancelled: int
    sellers_count: int = Field(..., description="Vendedores con pedidos facturables")
    total_income: Decimal = Field(
        ..., description="Total facturable: despachados + entregados"
    )


class ShiftClosureSummary(BaseModel):
    closure_date: date
    exported: bool = Field(
        ..., description="Todos los vendedores exportados y sin cambios posteriores"
    )
    cards: ClosureCards
    sellers: list[ClosureSellerRow]
