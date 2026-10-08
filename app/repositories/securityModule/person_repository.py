from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.securityModule.person import Person
from app.repositories.base_repository import BaseRepository
from app.schemas.securityModule.person_schema import PersonCreate, PersonUpdate


class RepositoryPerson(BaseRepository[Person, PersonCreate, PersonUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Person]:
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
person_repository = RepositoryPerson(Person)
