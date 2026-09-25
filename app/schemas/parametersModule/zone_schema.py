from pydantic import BaseModel, Field

from app.schemas.utils import partial_model


# Schema Base
class ZoneBase(BaseModel):
    name: str = Field(..., max_length=50, description="Nombre de la zona")
    commune_code: str = Field(..., max_length=3, description="Código de comuna")
    active: bool = True


class ZoneCreate(ZoneBase):
    pass


@partial_model
class ZoneUpdate(ZoneBase):
    pass


class ZoneResponse(ZoneBase):
    id_zone: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
