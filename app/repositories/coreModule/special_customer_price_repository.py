from decimal import Decimal
from typing import Any

from sqlalchemy import Select, delete, select
from sqlalchemy.dialects.postgresql import insert
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

    # ------------------------------------------------------------------
    # Panel de administración: precios especiales de un cliente
    # ------------------------------------------------------------------
    @staticmethod
    def _client_prices_select(id_client: int) -> Select:
        return (
            select(
                Product.id_product,
                Product.code.label("product_code"),
                Product.name.label("product_name"),
                Product.active.label("product_active"),
                Product.base_price,
                SpecialCustomerPrice.agreed_price,
            )
            .join(Product, Product.id_product == SpecialCustomerPrice.id_product)
            .where(SpecialCustomerPrice.id_client == id_client)
        )

    # Todos los precios del cliente (incluye productos inactivos), por código
    def get_client_prices(self, db: Session, id_client: int) -> list[Any]:
        stmt = self._client_prices_select(id_client).order_by(Product.code)
        return list(db.execute(stmt).all())

    def get_client_price(
        self, db: Session, id_client: int, id_product: int
    ) -> Any | None:
        stmt = self._client_prices_select(id_client).where(
            SpecialCustomerPrice.id_product == id_product
        )
        return db.execute(stmt).one_or_none()

    # Crea o actualiza el precio (único por cliente y producto) en una sola
    # sentencia: dos administradores a la vez no generan duplicados. Sin commit.
    def upsert_price(
        self, db: Session, *, id_client: int, id_product: int, agreed_price: Decimal
    ) -> None:
        stmt = insert(SpecialCustomerPrice).values(
            id_client=id_client, id_product=id_product, agreed_price=agreed_price
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_special_price_client_product",
            set_={"agreed_price": stmt.excluded.agreed_price},
        )
        db.execute(stmt)

    # Borra el precio; devuelve cuántas filas borró (0 = no existía). Sin commit.
    def delete_price(self, db: Session, *, id_client: int, id_product: int) -> int:
        result = db.execute(
            delete(SpecialCustomerPrice)
            .where(
                SpecialCustomerPrice.id_client == id_client,
                SpecialCustomerPrice.id_product == id_product,
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount  # type: ignore


# Intancia del repositorio inyectando el modelo ORM
special_customer_price_repository = RepositorySpecialCustomerPrice(SpecialCustomerPrice)
