from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coreModule.client import Client
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.client_schema import ClientCreate, ClientUpdate


class RepositoryClient(BaseRepository[Client, ClientCreate, ClientUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Client]:
        stmt = select(self.model)

        if only_active:
            stmt = stmt.where(self.model.active.is_(True))

        stmt = (
            stmt.order_by(*[col.asc() for col in self._primary_key_columns])
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    # Buscar cliente por su nombre
    def search_by_name(
        self, db: Session, *, name: str, limit: int = 10
    ) -> list[Client]:
        stmt = (
            select(Client)
            .where(Client.name.ilike(f"%{name}%"), Client.active.is_(True))
            .order_by(Client.name)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())


# Intancia del repositorio inyectando el modelo ORM
client_repository = RepositoryClient(Client)
