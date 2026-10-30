from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

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

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# Panel de administración: clientes REGISTRADOS
# -----------------------------------------------------
# Los temporales (is_registered=False, creados desde /orders/new-client) no se
# gestionan aquí: los borra la purga mensual. Por eso no se expone is_registered:
# el servicio lo fija en True al crear.
PHONE_PATTERN = r"^\d{10}$"


class ClientAdminCreate(BaseModel):
    name: UpperText = Field(..., max_length=200)
    phone: str | None = Field(None, pattern=PHONE_PATTERN, description="10 dígitos")
    address: UpperText | None = Field(None, max_length=200)
    id_neighborhood: int = Field(..., gt=0, description="Barrio del cliente")
    active: bool = True


# PATCH parcial. `active` desactiva (False) o reactiva (True) al cliente.
@partial_model
class ClientAdminUpdate(ClientAdminCreate):
    pass


@dataclass(frozen=True)
class ClientAdminFilters:
    """Filtros del listado de administración (ya validados por el router)."""

    search: str | None = None  # nombre (contiene) o teléfono (empieza por)
    active: bool | None = None  # None = activos e inactivos
    id_zone: int | None = None


class ClientAdminRow(BaseModel):
    id_client: int
    name: str
    phone: str | None
    address: str | None
    id_neighborhood: int
    neighborhood_name: str
    id_zone: int
    zone_name: str
    active: bool
    special_prices_count: int = Field(
        ..., description="Productos con precio especial pactado"
    )
    routes_count: int = Field(..., description="Rutas a las que está asignado")

    model_config = ConfigDict(from_attributes=True)
