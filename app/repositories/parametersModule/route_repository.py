from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.parametersModule.route import Route
from app.repositories.base_repository import BaseRepository
from app.schemas.parametersModule.route_schema import RouteCreate, RouteUpdate


class RepositoryRoute(BaseRepository[Route, RouteCreate, RouteUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Route]:
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
route_repository = RepositoryRoute(Route)
