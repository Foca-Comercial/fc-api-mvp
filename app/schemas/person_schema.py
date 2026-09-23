from pydantic import BaseModel, EmailStr, Field


# Atributos compartidos
class PersonBase(BaseModel):
    name: str = Field(..., max_length=500, description="Nombre de la persona")
    last_name: str = Field(..., max_length=500, description="Apellido de la persona")
    phone: str | None = Field(None, max_length=10, description="Teléfono de contacto")
    email: EmailStr | None = Field(
        None, max_length=50, description="Correo electrónico"
    )
    active: bool = True


# Esquema para crear (lo que llega por POST)
class PersonCreate(PersonBase):
    pass


# Esquema para actualizar (lo que llega por PUT/PATCH)
class PersonUpdate(BaseModel):
    name: str | None = Field(None, max_length=500)
    last_name: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=10)
    email: EmailStr | None = Field(None, max_length=50)
    active: bool | None = None


# Esquema de respuesta (lo que devuelve la API)
class PersonResponse(PersonBase):
    id_person: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
