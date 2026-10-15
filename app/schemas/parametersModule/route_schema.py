from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from app.models.parametersModule.route import DayWeek
from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText


# Schema Base
class RouteBase(BaseModel):
    name: UpperText = Field(..., max_length=50, description="Nombre de la ruta")
    day_week: DayWeek = Field(..., description="Día de la semana")
    departure_time: time = Field(..., description="Hora de salida (HH:MM)")
    active: bool = True


class RouteCreate(RouteBase):
    pass


@partial_model
class RouteUpdate(RouteBase):
    pass


class RouteResponse(RouteBase):
    id_route: int

    model_config = ConfigDict(from_attributes=True)
