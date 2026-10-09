from sqlalchemy.orm import Session

from app.models.coreModule.product import Product
from app.repositories.coreModule.product_repository import product_repository
from app.schemas.coreModule.product_schema import (
    ProductCatalogItem,
    ProductCreate,
    ProductUpdate,
)
from app.services.base_service import BaseService, UniqueRule


class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    unique_rules = (UniqueRule("code", "Código de producto"),)

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=product_repository, entity_name="Producto")

    # Obtener listado de productos con sus precios (id_client para precios especiales)
    def get_catalog(
        self, db: Session, *, id_client: int | None = None
    ) -> list[ProductCatalogItem]:
        rows = self.repository.get_catalog(db, id_client=id_client)
        return [
            ProductCatalogItem(
                id_product=p.id_product,
                code=p.code,
                name=p.name,
                base_price=p.base_price,
                agreed_price=agreed_price,
                effective_price=agreed_price
                if agreed_price is not None
                else p.base_price,
            )
            for p, agreed_price in rows
        ]


# Instancia única para inyectar en el router
product_service = ProductService()
