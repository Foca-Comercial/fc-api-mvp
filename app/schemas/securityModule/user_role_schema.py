from pydantic import BaseModel, ConfigDict, Field

from app.utils.helpers.schema_helper import partial_model


# Schema Base
class UserRoleBase(BaseModel):
    id_user: int = Field(..., gt=0, description="Usuario asociado")
    id_role: int = Field(..., gt=0, description="Rol asignado")


class UserRoleCreate(UserRoleBase):
    pass


@partial_model
class UserRoleUpdate(UserRoleBase):
    pass


class UserRoleResponse(UserRoleBase):
    id_user_role: int

    model_config = ConfigDict(from_attributes=True)
