from pydantic import BaseModel, ConfigDict, Field

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

    model_config = ConfigDict(from_attributes=True)
