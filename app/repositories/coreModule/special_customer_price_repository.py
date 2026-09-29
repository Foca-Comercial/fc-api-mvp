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
    pass


# Intancia del repositorio inyectando el modelo ORM
special_customer_price_repository = RepositorySpecialCustomerPrice(SpecialCustomerPrice)
