from pydantic import BaseModel, ConfigDict, Field

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText


# Schema Base
class NeighborhoodBase(BaseModel):
    name: UpperText = Field(..., max_length=50, description="Nombre del barrio")
    active: bool = True
    id_zone: int = Field(..., description="Zona a la que pertenece el barrio")


class NeighborhoodCreate(NeighborhoodBase):
    pass


@partial_model
class NeighborhoodUpdate(NeighborhoodBase):
    pass


class NeighborhoodResponse(NeighborhoodBase):
    id_neighborhood: int

    model_config = ConfigDict(from_attributes=True)
