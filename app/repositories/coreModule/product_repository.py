from app.models.coreModule.product import Product
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.product_schema import ProductCreate, ProductUpdate


class RepositoryProduct(BaseRepository[Product, ProductCreate, ProductUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
product_repository = RepositoryProduct(Product)
