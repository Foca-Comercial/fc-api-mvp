from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.order_detail_schema import OrderDetailResponse
from app.services.coreModule.order_detail_service import order_detail_service

# Solo lectura: los detalles de un pedido se crean/editan/eliminan únicamente
# vía PUT /orders/{id}/items-order (OrderService.sync_items), que valida el
# estado del pedido y recalcula order_total.
router = SecuredRouter(prefix="/orders_details", tags=["OrdersDetails"])


@router.get("/", response_model=list[OrderDetailResponse])
def get_all_orders_details(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_detail_service.get_all(db, skip=skip, limit=limit)


@router.get("/{order_detail_id}", response_model=OrderDetailResponse)
def get_order_detail(order_detail_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_detail_service.get(db, id=order_detail_id)
