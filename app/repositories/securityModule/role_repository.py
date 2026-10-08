from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.securityModule.role import Role
from app.repositories.base_repository import BaseRepository
from app.schemas.securityModule.role_schema import RoleCreate, RoleUpdate


class RepositoryRole(BaseRepository[Role, RoleCreate, RoleUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Role]:
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
role_repository = RepositoryRole(Role)
