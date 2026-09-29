from app.models.coreModule.order import Order
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.order_schema import OrderCreate, OrderUpdate


class RepositoryOrder(BaseRepository[Order, OrderCreate, OrderUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
order_repository = RepositoryOrder(Order)
