from pydantic import BaseModel, ConfigDict, Field

from app.utils.helpers.schema_helper import partial_model


# Schema Base
class UserVehicleBase(BaseModel):
    code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Código identificador (2 caracteres)",
    )
    id_user_role: int = Field(..., gt=0, description="Usuario-rol (vendedor)")
    id_vehicle: int = Field(..., gt=0, description="Vehículo asignado")


class UserVehicleCreate(UserVehicleBase):
    pass


@partial_model
class UserVehicleUpdate(UserVehicleBase):
    pass


class UserVehicleResponse(UserVehicleBase):
    id_user_vehicle: int

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# Asignacion Conductor - Vehiculo
# -----------------------------------------------------
class DriverVehicleDropdownResponse(BaseModel):
    id_user_vehicle: int
    code: str
    driver_name: str
    vehicle_name: str

    model_config = ConfigDict(from_attributes=True)
