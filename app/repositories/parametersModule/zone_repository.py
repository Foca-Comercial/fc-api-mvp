from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.parametersModule.zone import Zone
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.zone_schema import ZoneCreate, ZoneUpdate


class RepositoryZone(BaseRepository[Zone, ZoneCreate, ZoneUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Zone]:
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
zone_repository = RepositoryZone(Zone)
