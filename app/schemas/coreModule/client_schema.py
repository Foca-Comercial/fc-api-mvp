from pydantic import BaseModel, Field

from app.schemas.utils import partial_model


# Schemba Base
class ClientBase(BaseModel):
    name: str = Field(
        ..., max_length=200, description="Nombre o razón social del cliente"
    )
    phone: str | None = Field(None, max_length=10)
    address: str | None = Field(None, max_length=200)
    id_neighborhood: int = Field(..., description="Barrio al que pertenece el cliente")
    is_registered: bool = False
    active: bool = True


class ClientCreate(ClientBase):
    pass


@partial_model
class ClientUpdate(ClientBase):
    pass


class ClientResponse(ClientBase):
    id_client: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
