from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coreModule.product import Product
from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.special_customer_price_schema import (
    SpecialCustomerPriceCreate,
    SpecialCustomerPriceUpdate,
)


class RepositorySpecialCustomerPrice(
    BaseRepository[
        SpecialCustomerPrice, SpecialCustomerPriceCreate, SpecialCustomerPriceUpdate
    ]
):
    # Pedidos por ruta: productos con precio especial de varios clientes en una
    # consulta, solo productos activos, ordenados por cliente y código.
    # Filas: (id_client, id_product, code, name, agreed_price)
    def get_products_for_clients(
        self, db: Session, client_ids: list[int]
    ) -> list[tuple]:
        if not client_ids:
            return []
        stmt = (
            select(
                SpecialCustomerPrice.id_client,
                Product.id_product,
                Product.code,
                Product.name,
                SpecialCustomerPrice.agreed_price,
            )
            .join(Product, Product.id_product == SpecialCustomerPrice.id_product)
            .where(
                SpecialCustomerPrice.id_client.in_(client_ids),
                Product.active.is_(True),
            )
            .order_by(SpecialCustomerPrice.id_client, Product.code)
        )
        return list(db.execute(stmt).all())


# Intancia del repositorio inyectando el modelo ORM
special_customer_price_repository = RepositorySpecialCustomerPrice(SpecialCustomerPrice)
