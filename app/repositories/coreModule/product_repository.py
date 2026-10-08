from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coreModule.product import Product
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.product_schema import ProductCreate, ProductUpdate


class RepositoryProduct(BaseRepository[Product, ProductCreate, ProductUpdate]):
    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, only_active: bool = True
    ) -> list[Product]:
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
product_repository = RepositoryProduct(Product)
