from sqlalchemy.orm import Session

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
    ClientSpecialPriceRow,
    ClientSpecialPriceSet,
    SpecialCustomerPriceCreate,
    SpecialCustomerPriceUpdate,
)
from app.services.base_service import BaseService
from app.services.coreModule.client_service import client_service
from app.services.validation import ReferenceRule, UniqueTogether
from app.utils.exceptions.business_exceptions import EntityNotFoundError


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

    # ------------------------------------------------------------------
    # Panel de administración: precios especiales de un cliente REGISTRADO.
    # Se identifican por (cliente, producto), que es único. No tienen `active`:
    # quitar un precio lo borra (el pedido ya tomado conserva el suyo en su
    # detalle, así que no se pierde historial).
    # ------------------------------------------------------------------
    def list_for_client(
        self, db: Session, *, id_client: int
    ) -> list[ClientSpecialPriceRow]:
        client_service.get_registered(db, id_client)
        rows = special_customer_price_repository.get_client_prices(db, id_client)
        return [
            ClientSpecialPriceRow.model_validate(row, from_attributes=True)
            for row in rows
        ]

    def set_for_client(
        self,
        db: Session,
        *,
        id_client: int,
        id_product: int,
        obj_in: ClientSpecialPriceSet,
    ) -> ClientSpecialPriceRow:
        """Asigna o cambia el precio pactado del cliente para el producto."""
        client_service.get_registered(db, id_client)
        existing = special_customer_price_repository.get_client_price(
            db, id_client, id_product
        )
        if existing is None:
            # Un precio NUEVO solo para un producto que exista y esté activo;
            # el de un producto que se desactivó después sí se puede editar.
            self._ensure_reference(
                db,
                product_repository,
                id_product,
                field="id_product",
                label="Producto",
            )
        special_customer_price_repository.upsert_price(
            db,
            id_client=id_client,
            id_product=id_product,
            agreed_price=obj_in.agreed_price,
        )
        db.commit()
        return self._client_price(db, id_client, id_product)

    def remove_for_client(
        self, db: Session, *, id_client: int, id_product: int
    ) -> None:
        client_service.get_registered(db, id_client)
        deleted = special_customer_price_repository.delete_price(
            db, id_client=id_client, id_product=id_product
        )
        if deleted == 0:
            raise EntityNotFoundError("Precio especial del producto", id_product)
        db.commit()

    @staticmethod
    def _client_price(
        db: Session, id_client: int, id_product: int
    ) -> ClientSpecialPriceRow:
        row = special_customer_price_repository.get_client_price(
            db, id_client, id_product
        )
        if row is None:
            raise EntityNotFoundError("Precio especial del producto", id_product)
        return ClientSpecialPriceRow.model_validate(row, from_attributes=True)


# Instancia única para inyectar en el customerr
special_customer_price_service = SpecialCustomerPriceService()
