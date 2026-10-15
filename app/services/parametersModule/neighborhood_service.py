from sqlalchemy.orm import Session

from app.models.parametersModule.neighborhood import Neighborhood
from app.repositories.parametersModule.neighborhood_repository import (
    neighborhood_repository,
)
from app.repositories.parametersModule.zone_repository import zone_repository
from app.schemas.parametersModule.neighborhood_schema import (
    NeighborhoodCreate,
    NeighborhoodDropdownResponse,
    NeighborhoodUpdate,
)
from app.services.base_service import BaseService


class NeighborhoodService(
    BaseService[Neighborhood, NeighborhoodCreate, NeighborhoodUpdate]
):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=neighborhood_repository, entity_name="Barrio")

    # Selector de barrio del formulario de pedido para cliente nuevo
    def get_dropdown(self, db: Session) -> list[NeighborhoodDropdownResponse]:
        return [
            NeighborhoodDropdownResponse.model_validate(row)
            for row in neighborhood_repository.get_dropdown(db)
        ]

    def _validate_before_create(self, db: Session, obj_in: NeighborhoodCreate) -> None:
        self._ensure_reference(
            db, zone_repository, obj_in.id_zone, field="id_zone", label="Zona"
        )
        self._ensure_unique(
            db,
            "name",
            obj_in.name,
            label="Barrio en esta zona",
            normalized=True,
            id_zone=obj_in.id_zone,
        )

    def _validate_before_update(
        self, db: Session, obj_in: NeighborhoodUpdate, existing: Neighborhood
    ) -> None:
        # La zona solo se revalida si cambia: un barrio de una zona que se
        # desactivó después debe poder seguir editándose.
        if obj_in.id_zone is not None and obj_in.id_zone != existing.id_zone:
            self._ensure_reference(
                db, zone_repository, obj_in.id_zone, field="id_zone", label="Zona"
            )

        # La unicidad depende de la pareja (nombre, zona): se evalúa con los
        # valores finales, mezclando lo enviado con lo que ya tenía el registro.
        if obj_in.name is not None or obj_in.id_zone is not None:
            self._ensure_unique(
                db,
                "name",
                obj_in.name if obj_in.name is not None else existing.name,
                label="Barrio en esta zona",
                normalized=True,
                exclude=existing,
                id_zone=obj_in.id_zone
                if obj_in.id_zone is not None
                else existing.id_zone,
            )


# Instancia única para inyectar en el router
neighborhood_service = NeighborhoodService()
