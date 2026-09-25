from pydantic import BaseModel, Field

from app.schemas.utils import partial_model


# Schema Base
class UserBase(BaseModel):
    username: str = Field(..., max_length=100, description="Nombre de usuario")
    active: bool = True
    id_person: int = Field(..., description="Persona asociada a este usuario")


class UserCreate(UserBase):
    password: str = Field(
        ..., min_length=8, max_length=200, description="Contraseña en texto plano"
    )


@partial_model
class UserUpdate(UserBase):
    pass


class UserResponse(UserBase):
    id_user: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
