from app.models.coreModule.special_customer_price import SpecialCustomerPrice
from app.repositories.coreModule.client_repository import (
    client_repository,
)
from app.repositories.coreModule.product_repository import (
    product_repository,
)
from app.repositories.coreModule.special_customer_price_repository import (
    special_customer_price_repository,
)
from app.schemas.coreModule.special_customer_price_schema import (
    SpecialCustomerPriceCreate,
    SpecialCustomerPriceUpdate,
)
from app.services.base_service import BaseService
from app.services.validation import ReferenceRule, UniqueTogether


class SpecialCustomerPriceService(
    BaseService[
        SpecialCustomerPrice, SpecialCustomerPriceCreate, SpecialCustomerPriceUpdate
    ]
):
    references = (
        ReferenceRule("id_client", "Cliente", client_repository),
        ReferenceRule("id_product", "Producto", product_repository),
    )
    unique_together = (
        UniqueTogether("Cliente y producto", ("id_client", "id_product")),
    )

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(
            repository=special_customer_price_repository,
            entity_name="ClientePrecioEspecial",
        )


# Instancia única para inyectar en el customerr
special_customer_price_service = SpecialCustomerPriceService()
