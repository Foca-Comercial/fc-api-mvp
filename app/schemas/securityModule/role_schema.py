from pydantic import BaseModel, Field

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

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
