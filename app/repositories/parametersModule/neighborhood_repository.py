from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.parametersModule.neighborhood import Neighborhood
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


# Intancia del repositorio inyectando el modelo ORM
neighborhood_repository = RepositoryNeighborhood(Neighborhood)
