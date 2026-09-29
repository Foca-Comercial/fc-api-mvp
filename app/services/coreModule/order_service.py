from app.models.coreModule.order import Order
from app.repositories.coreModule.order_repository import order_repository
from app.schemas.coreModule.order_schema import OrderCreate, OrderUpdate
from app.services.base_service import BaseService


class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=order_repository, entity_name="Orden")


# Instancia única para inyectar en el router
order_service = OrderService()
