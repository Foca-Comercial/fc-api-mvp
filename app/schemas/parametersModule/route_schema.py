from datetime import time

from pydantic import BaseModel, Field

from app.models.parametersModule.route import DayWeek
from app.utils.helpers.schema_helper import partial_model


# Schema Base
class RouteBase(BaseModel):
    name: str = Field(..., max_length=50, description="Nombre de la ruta")
    day_week: DayWeek = Field(
        ..., description="Día de la semana (1=Lunes ... 7=Domingo)"
    )
    departure_time: time = Field(..., description="Hora de salida programada")
    active: bool = True


class RouteCreate(RouteBase):
    pass


@partial_model
class RouteUpdate(RouteBase):
    pass


class RouteResponse(RouteBase):
    id_route: int

    class Config:
        from_attributes = (
            True  # Permite mapear directamente el objeto de SQLAlchemy al DTO
        )
