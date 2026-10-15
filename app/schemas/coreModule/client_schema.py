from pydantic import BaseModel, Field

from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText


# Schemba Base
class ClientBase(BaseModel):
    name: UpperText = Field(..., max_length=200)
    phone: str | None = Field(None, description="10 dígitos")
    address: UpperText | None = Field(None, max_length=200)
    id_neighborhood: int = Field(..., gt=0, description="Barrio del cliente")
    is_registered: bool = False
    active: bool = True


class ClientCreate(ClientBase):
    pass


# -----------------------------------------------------
# Creacion de un nuevo cliente en la vista principal
# -----------------------------------------------------
class NewClientInput(BaseModel):
    # Misma normalización que ClientBase (strip + mayúsculas)
    name: UpperText = Field(..., max_length=200)
    phone: str | None = Field(None, max_length=10)
    address: UpperText | None = Field(None, max_length=200)
    id_neighborhood: int = Field(..., description="Barrio del cliente")


@partial_model
class ClientUpdate(ClientBase):
    pass


class ClientResponse(ClientBase):
    id_client: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
