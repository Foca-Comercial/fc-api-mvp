from pydantic import BaseModel, ConfigDict, Field

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

    model_config = ConfigDict(from_attributes=True)
