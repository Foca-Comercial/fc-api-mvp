from pydantic import BaseModel, Field

from app.utils.helpers.schema_helper import partial_model


# Schema Base
class ClientRouteBase(BaseModel):
    id_client: int = Field(..., gt=0, description="Cliente asociado a la ruta")
    id_route: int = Field(..., gt=0, description="Ruta asignada al cliente")


class ClientRouteCreate(ClientRouteBase):
    pass


@partial_model
class ClientRouteUpdate(ClientRouteBase):
    pass


class ClientRouteResponse(ClientRouteBase):
    id_client_route: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
