from pydantic import BaseModel, Field

from app.schemas.utils import partial_model


# Schema Base
class UserRoleBase(BaseModel):
    id_user: int = Field(..., description="Usuario asociado")
    id_role: int = Field(..., description="Rol asignado")


class UserRoleCreate(UserRoleBase):
    pass


@partial_model
class UserRoleUpdate(UserRoleBase):
    pass


class UserRoleResponse(UserRoleBase):
    id_user_role: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
