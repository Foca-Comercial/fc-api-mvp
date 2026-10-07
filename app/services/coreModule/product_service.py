from app.models.coreModule.product import Product
from app.repositories.coreModule.product_repository import product_repository
from app.schemas.coreModule.product_schema import ProductCreate, ProductUpdate
from app.services.base_service import BaseService, UniqueRule


class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    unique_rules = (UniqueRule("code", "Código de producto"),)

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=product_repository, entity_name="Producto")


# Instancia única para inyectar en el router
product_service = ProductService()
