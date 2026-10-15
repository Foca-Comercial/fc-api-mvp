from pydantic import BaseModel, ConfigDict, Field

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText


# Schema Base
class RoleBase(BaseModel):
    name: UpperText = Field(..., max_length=100, description="Nombre del rol")
    description: UpperText | None = Field(None, max_length=200)
    active: bool = True


class RoleCreate(RoleBase):
    pass


@partial_model
class RoleUpdate(RoleBase):
    pass


class RoleResponse(RoleBase):
    id_role: int

    model_config = ConfigDict(from_attributes=True)
