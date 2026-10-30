from typing import Any

from sqlalchemy import Select, exists, func, null, or_, select
from sqlalchemy.orm import Session

from app.models.coreModule.order_detail import OrderDetail
from app.models.coreModule.product import Product
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.repositories.base_repository import BaseRepository
from app.repositories.pagination import paginate
from app.schemas.common.page_schema import PageParams
from app.schemas.coreModule.product_schema import (
    ProductAdminFilters,
    ProductCreate,
    ProductUpdate,
)


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

    # Obtener listado de productos con sus precios (id_client para precios especiales)
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
                .order_by(Product.code)
            )
        return db.execute(stmt).all()

    # ------------------------------------------------------------------
    # Panel de administración
    # ------------------------------------------------------------------
    @staticmethod
    def _admin_conditions(filters: ProductAdminFilters) -> list[Any]:
        conditions: list[Any] = []
        if filters.search:
            conditions.append(
                or_(
                    Product.code.startswith(filters.search, autoescape=True),
                    Product.name.icontains(filters.search, autoescape=True),
                )
            )
        if filters.active is not None:
            conditions.append(Product.active.is_(filters.active))
        return conditions

    @staticmethod
    def _admin_select() -> Select:
        """Fila del listado. Conteo de precios especiales y si tiene pedidos
        (EXISTS sobre idx_order_detail_product): solo para las filas de la página."""
        special_prices = (
            select(func.count(SpecialCustomerPrice.id_client_price))
            .where(SpecialCustomerPrice.id_product == Product.id_product)
            .correlate(Product)
            .scalar_subquery()
        )
        in_use = (
            exists()
            .where(OrderDetail.id_product == Product.id_product)
            .correlate(Product)
        )
        return select(
            Product.id_product,
            Product.code,
            Product.name,
            Product.description,
            Product.base_price,
            Product.active,
            special_prices.label("special_prices_count"),
            in_use.label("in_use"),
        )

    # Una página de productos, por código
    def get_admin_page(
        self, db: Session, filters: ProductAdminFilters, params: PageParams
    ) -> tuple[list[Any], int]:
        conditions = self._admin_conditions(filters)
        stmt = (
            self._admin_select()
            .where(*conditions)
            .order_by(Product.code, Product.id_product)
        )
        count_stmt = select(Product.id_product).where(*conditions)
        return paginate(db, stmt, params, count_stmt=count_stmt)

    def get_admin_row(self, db: Session, id_product: int) -> Any | None:
        stmt = self._admin_select().where(Product.id_product == id_product)
        return db.execute(stmt).one_or_none()

    # ¿Algún pedido tiene este producto? (su código ya no se puede cambiar)
    def has_orders(self, db: Session, id_product: int) -> bool:
        stmt = select(exists().where(OrderDetail.id_product == id_product))
        return bool(db.scalar(stmt))


# Intancia del repositorio inyectando el modelo ORM
product_repository = RepositoryProduct(Product)
