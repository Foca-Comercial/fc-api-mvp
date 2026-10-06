from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

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

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
