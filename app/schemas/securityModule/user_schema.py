from pydantic import BaseModel, Field

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import LowerText


# Schema Base
class UserBase(BaseModel):
    username: LowerText = Field(..., max_length=100, description="Nombre de usuario")
    active: bool = True
    id_person: int = Field(..., description="Persona asociada a este usuario")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=200)


@partial_model
class UserUpdate(UserBase):
    pass


class UserResponse(UserBase):
    id_user: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
