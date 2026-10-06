from pydantic import BaseModel, EmailStr, Field

from app.utils.helpers.schema_helper import partial_model


# Schema Base
class PersonBase(BaseModel):
    name: str = Field(..., max_length=100, description="Nombre de la persona")
    last_name: str = Field(..., max_length=100, description="Apellido de la persona")
    phone: str | None = Field(None, max_length=10, description="Teléfono de contacto")
    email: EmailStr | None = Field(
        None, max_length=50, description="Correo electrónico"
    )
    active: bool = True


class PersonCreate(PersonBase):
    pass


@partial_model
class PersonUpdate(PersonBase):
    pass


class PersonResponse(PersonBase):
    id_person: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
