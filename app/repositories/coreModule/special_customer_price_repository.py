from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

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
    # Precios especiales de varios clientes en una consulta:
    # {(id_client, id_product): agreed_price}
    def get_for_clients(
        self, db: Session, client_ids: list[int]
    ) -> dict[tuple[int, int], Decimal]:
        if not client_ids:
            return {}
        stmt = select(
            SpecialCustomerPrice.id_client,
            SpecialCustomerPrice.id_product,
            SpecialCustomerPrice.agreed_price,
        ).where(SpecialCustomerPrice.id_client.in_(client_ids))
        return {
            (row.id_client, row.id_product): row.agreed_price
            for row in db.execute(stmt).all()
        }


# Intancia del repositorio inyectando el modelo ORM
special_customer_price_repository = RepositorySpecialCustomerPrice(SpecialCustomerPrice)
