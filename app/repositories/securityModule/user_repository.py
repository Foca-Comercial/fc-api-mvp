from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.securityModule.user import User
from app.models.securityModule.user_role import UserRole
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

    def get_by_username_with_roles(self, db: Session, username: str) -> User | None:
        stmt = (
            select(User)
            .options(joinedload(User.user_roles).joinedload(UserRole.role))
            .where(User.username == username)
        )
        return db.scalars(stmt).unique().first()


# Intancia del repositorio inyectando el modelo ORM
user_repository = RepositoryUser(User)
