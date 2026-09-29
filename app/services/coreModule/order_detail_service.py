from app.models.coreModule.order_detail import OrderDetail
from app.repositories.coreModule.order_detail_repository import order_detail_repository
from app.schemas.coreModule.order_detail_schema import (
    OrderDetailCreate,
    OrderDetailUpdate,
)
from app.services.base_service import BaseService


class OrderDetailService(
    BaseService[OrderDetail, OrderDetailCreate, OrderDetailUpdate]
):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=order_detail_repository, entity_name="OrdenDetalle")


# Instancia única para inyectar en el detailr
order_detail_service = OrderDetailService()
