from pydantic import BaseModel, Field

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText


# Schema Base
class ZoneBase(BaseModel):
    name: UpperText = Field(..., max_length=50, description="Nombre de la zona")
    commune_code: UpperText = Field(..., max_length=3, description="Código de comuna")
    active: bool = True


class ZoneCreate(ZoneBase):
    pass


@partial_model
class ZoneUpdate(ZoneBase):
    pass


class ZoneResponse(ZoneBase):
    id_zone: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
