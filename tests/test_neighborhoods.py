"""Barrios: selector para el formulario de cliente nuevo y validación de zona."""

from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.zone import Zone
from app.schemas.parametersModule.neighborhood_schema import (
    NeighborhoodCreate,
    NeighborhoodUpdate,
)
from app.services.parametersModule.neighborhood_service import neighborhood_service
from tests.helpers import API


def test_selector_de_barrios_para_gestor(client, db, data):
    inactive_zone = Zone(name="ZONA INACTIVA", commune_code="Z98", active=False)
    db.add(inactive_zone)
    db.flush()
    inactive = Neighborhood(
        name="BARRIO INACTIVO", id_zone=data.neighborhood.id_zone, active=False
    )
    in_inactive_zone = Neighborhood(name="BARRIO HUERFANO", id_zone=inactive_zone.id_zone)
    db.add_all([inactive, in_inactive_zone])
    db.commit()

    response = client.get(f"{API}/neighborhoods/dropdown")

    assert response.status_code == 200, response.text
    rows = {r["id_neighborhood"]: r for r in response.json()}
    assert rows[data.neighborhood.id_neighborhood]["zone_name"] == "ZONA TEST"
    assert inactive.id_neighborhood not in rows
    assert in_inactive_zone.id_neighborhood not in rows


def test_el_listado_completo_sigue_siendo_solo_de_admin(client):
    assert client.get(f"{API}/neighborhoods/").status_code == 403


def test_crear_barrio_valida_la_zona(db, data):
    """Regresión: el servicio importaba el MÓDULO zone_repository en vez de la
    instancia, y crear o cambiar la zona de un barrio fallaba con 500."""
    created = neighborhood_service.create(
        db,
        obj_in=NeighborhoodCreate(name="barrio nuevo", id_zone=data.neighborhood.id_zone),
    )
    assert created.name == "BARRIO NUEVO"

    other_zone = Zone(name="OTRA ZONA", commune_code="Z97")
    db.add(other_zone)
    db.commit()
    updated = neighborhood_service.update(
        db, id=created.id_neighborhood, obj_in=NeighborhoodUpdate(id_zone=other_zone.id_zone)
    )
    assert updated.id_zone == other_zone.id_zone
