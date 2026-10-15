"""Rutas: varios días por ruta (R1)."""

from datetime import time

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.parametersModule.route import Route
from app.schemas.parametersModule.route_schema import RouteCreate, RouteUpdate
from app.services.parametersModule.route_service import route_service
from app.utils.enums.day_week import DayWeek


def _create_route(db, **overrides) -> Route:
    payload = {"name": "ruta test", "days_week": [1], "departure_time": "06:30"}
    return route_service.create(db, obj_in=RouteCreate(**{**payload, **overrides}))


def test_ruta_con_varios_dias_se_guarda_ordenada_y_sin_repetidos(db):
    route = _create_route(db, days_week=[4, 1, 1])

    db.expire_all()
    assert route.days_week == [DayWeek.MONDAY, DayWeek.THURSDAY]
    assert route.name == "RUTA TEST"
    assert route.departure_time == time(6, 30)


@pytest.mark.parametrize("days", [[], [0], [8]])
def test_dias_invalidos_se_rechazan_en_el_schema(days):
    with pytest.raises(ValidationError):
        RouteCreate(name="ruta", days_week=days, departure_time="06:30")  # type: ignore


def test_actualizar_solo_los_dias(db):
    route = _create_route(db, days_week=[1, 4])

    route_service.update(db, id=route.id_route, obj_in=RouteUpdate(days_week=[7, 6]))  # type: ignore

    db.expire_all()
    assert route.days_week == [6, 7]
    assert route.name == "RUTA TEST"  # lo no enviado no cambia


def test_la_bd_rechaza_una_ruta_sin_dias(db):
    """El CHECK de la BD respalda la validación del schema."""
    db.add(Route(name="SIN DIAS", days_week=[], departure_time=time(8, 0)))

    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
