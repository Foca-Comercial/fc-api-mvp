from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.zone import Zone
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.neighborhood_schema import (
    NeighborhoodCreate,
    NeighborhoodUpdate,
)


class RepositoryNeighborhood(
    BaseRepository[Neighborhood, NeighborhoodCreate, NeighborhoodUpdate]
):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Neighborhood]:
        stmt = select(self.model)

        if only_active:
            stmt = stmt.where(self.model.active.is_(True))

        stmt = (
            stmt.order_by(*[col.asc() for col in self._primary_key_columns])
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    # Barrios activos de zonas activas, con el nombre de la zona
    def get_dropdown(self, db: Session) -> list[tuple]:
        stmt = (
            select(
                Neighborhood.id_neighborhood,
                Neighborhood.name,
                Zone.id_zone,
                Zone.name.label("zone_name"),
            )
            .join(Zone, Zone.id_zone == Neighborhood.id_zone)
            .where(Neighborhood.active.is_(True), Zone.active.is_(True))
            .order_by(Neighborhood.name)
        )
        return list(db.execute(stmt).all())


# Intancia del repositorio inyectando el modelo ORM
neighborhood_repository = RepositoryNeighborhood(Neighborhood)
