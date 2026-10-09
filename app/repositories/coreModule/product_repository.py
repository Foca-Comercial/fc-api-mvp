from sqlalchemy import null, select
from sqlalchemy.orm import Session

from app.models.coreModule.product import Product
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
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

    def get_catalog(self, db: Session, *, id_client: int | None = None):
        if id_client is not None:
            stmt = (
                select(Product, SpecialCustomerPrice.agreed_price)
                .outerjoin(
                    SpecialCustomerPrice,
                    (SpecialCustomerPrice.id_product == Product.id_product)
                    & (SpecialCustomerPrice.id_client == id_client),
                )
                .where(Product.active.is_(True))
                .order_by(Product.name)
            )
        else:
            stmt = (
                select(Product, null().label("agreed_price"))
                .where(Product.active.is_(True))
                .order_by(Product.name)
            )
        return db.execute(stmt).all()


# Intancia del repositorio inyectando el modelo ORM
product_repository = RepositoryProduct(Product)
