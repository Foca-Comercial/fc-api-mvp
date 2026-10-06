from pydantic import BaseModel, Field

from app.utils.helpers.schema_helper import partial_model


# Schema Base
class UserVehicleBase(BaseModel):
    code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Código identificador (2 caracteres)",
    )
    id_user_role: int = Field(
        ..., description="Rol de usuario asociado (conductor + rol)"
    )
    id_vehicle: int = Field(..., description="Vehículo asignado")


class UserVehicleCreate(UserVehicleBase):
    pass


@partial_model
class UserVehicleUpdate(UserVehicleBase):
    pass


class UserVehicleResponse(UserVehicleBase):
    id_user_vehicle: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
