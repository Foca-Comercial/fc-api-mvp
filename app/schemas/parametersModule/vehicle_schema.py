from pydantic import BaseModel, Field

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText


# Schema Base
class VehicleBase(BaseModel):
    name: UpperText = Field(..., max_length=50, description="Nombre del vehículo")
    active: bool = True


class VehicleCreate(VehicleBase):
    pass


@partial_model
class VehicleUpdate(VehicleBase):
    pass


class VehicleResponse(VehicleBase):
    id_vehicle: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
