from pydantic import BaseModel, Field

from app.schemas.utils import partial_model


# Schema Base
class NeighborhoodBase(BaseModel):
    name: str = Field(..., max_length=50, description="Nombre del barrio")
    active: bool = True
    id_zone: int = Field(..., description="Zona a la que pertenece el barrio")


class NeighborhoodCreate(NeighborhoodBase):
    pass


@partial_model
class NeighborhoodUpdate(NeighborhoodBase):
    pass


class NeighborhoodResponse(NeighborhoodBase):
    id_neighborhood: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
