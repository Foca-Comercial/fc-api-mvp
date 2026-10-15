from datetime import time

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.utils.enums.day_week import DayWeek
from app.utils.helpers.schema_helper import partial_model
from app.utils.schema_types import UpperText


# Schema Base
class RouteBase(BaseModel):
    name: UpperText = Field(..., max_length=50, description="Nombre de la ruta")
    days_week: list[DayWeek] = Field(
        ...,
        min_length=1,
        description="Días en que sale la ruta (1 = lunes ... 7 = domingo)",
    )
    departure_time: time = Field(..., description="Hora de salida (HH:MM)")
    active: bool = True

    @field_validator("days_week")
    @classmethod
    def _unique_sorted_days(cls, value: list[DayWeek] | None) -> list[DayWeek] | None:
        # [4, 1, 1] -> [1, 4]: sin repetidos y en orden de la semana
        return sorted(set(value)) if value is not None else None

    @field_serializer("days_week")
    def _days_as_int(self, value: list[DayWeek] | None) -> list[int] | None:
        # Enteros planos hacia la BD (SMALLINT[]) y en el JSON de respuesta
        return [int(day) for day in value] if value is not None else None


class RouteCreate(RouteBase):
    pass


@partial_model
class RouteUpdate(RouteBase):
    pass


class RouteResponse(RouteBase):
    id_route: int

    model_config = ConfigDict(from_attributes=True)
