from pydantic import BaseModel, ConfigDict, Field

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

    model_config = ConfigDict(from_attributes=True)
