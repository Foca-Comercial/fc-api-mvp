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
        ..., description="Unidades de la factura global, sumando todos los precios"
    )


class ClosureCategoryTotals(BaseModel):
    """Ventas por tipo de factura y método de pago (las columnas del cuadre)."""

    pos_cash: Decimal = Field(..., description="POS en efectivo: la factura global")
    electronic_cash: Decimal
    pos_transfer: Decimal
    electronic_transfer: Decimal
    pos_credit: Decimal
    electronic_credit: Decimal


class ClosureSellerRow(BaseModel):
    id_user_vehicle: int
    seller_code: int = Field(
        ..., description="Código del vendedor sin ceros a la izquierda (Siigo)"
    )
    seller_name: str
    # Factura global (solo POS + efectivo)
    products: list[ClosureProduct] = Field(
        ..., description="Productos de la factura global (POS + efectivo)"
    )
    total_quantity: int = Field(..., description="Unidades de la factura global")
    consolidated_total: Decimal = Field(..., description="Total de la factura global")
    # Todas las ventas del vendedor
    orders_count: int = Field(..., description="Pedidos facturables (todas las categorías)")
    other_orders_count: int = Field(
        ..., description="Pedidos que no van a la factura global (hoja Otras facturas)"
    )
    unassigned_orders: int = Field(
        0,
        description="Pedidos sin conductor sumados a este vendedor (solo el de "
        "por defecto)",
    )
    totals: ClosureCategoryTotals
    total_sales: Decimal = Field(..., description="Todas las categorías")
    cash_to_collect: Decimal = Field(
        ..., description="Efectivo a recibir: POS efectivo + FE efectivo"
    )
    exported_at: datetime | None = Field(
        None, description="Última exportación de este vendedor y día"
    )
    export_outdated: bool = Field(
        False,
        description="Se exportó, pero algún pedido cambió después (estado, pago, "
        "factura, productos o vendedor)",
    )


class ClosureCards(BaseModel):
    total_orders: int = Field(..., description="Pedidos del día en cualquier estado")
    pending: int
    dispatched: int
    delivered: int
    cancelled: int
    cancelled_after_dispatch: int = Field(
        ..., description="Cancelados después de despacharse (devoluciones)"
    )
    sellers_count: int = Field(..., description="Vendedores con pedidos facturables")
    totals: ClosureCategoryTotals
    total_income: Decimal = Field(
        ..., description="Total facturable: despachados + entregados, todas las "
        "categorías"
    )
    cash_to_collect: Decimal = Field(
        ..., description="Efectivo a recibir: POS efectivo + FE efectivo"
    )


class ShiftClosureSummary(BaseModel):
    closure_date: date
    exported: bool = Field(
        ..., description="Todos los vendedores exportados y sin cambios posteriores"
    )
    cards: ClosureCards
    sellers: list[ClosureSellerRow]
