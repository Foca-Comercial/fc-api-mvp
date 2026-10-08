from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.securityModule.user import User
from app.repositories.base_repository import BaseRepository
from app.schemas.securityModule.user_schema import UserCreate, UserUpdate


class RepositoryUser(BaseRepository[User, UserCreate, UserUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[User]:
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
user_repository = RepositoryUser(User)
