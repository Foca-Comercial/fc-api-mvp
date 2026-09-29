from app.models.coreModule.order_detail import OrderDetail
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.order_detail_schema import (
    OrderDetailCreate,
    OrderDetailUpdate,
)


class RepositoryOrderDetail(
    BaseRepository[OrderDetail, OrderDetailCreate, OrderDetailUpdate]
):
    pass


# Intancia del repositorio inyectando el modelo ORM
order_detail_repository = RepositoryOrderDetail(OrderDetail)
