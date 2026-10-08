from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.order_detail_schema import (
    OrderDetailCreate,
    OrderDetailResponse,
    OrderDetailUpdate,
)
from app.services.coreModule.order_detail_service import order_detail_service

router = SecuredRouter(prefix="/orders_details", tags=["OrdersDetails"])


@router.get("/", response_model=list[OrderDetailResponse])
def get_all_orders_details(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_detail_service.get_all(db, skip=skip, limit=limit)


@router.get("/{order_detail_id}", response_model=OrderDetailResponse)
def get_order(order_detail_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_detail_service.get(db, id=order_detail_id)


@router.post(
    "/", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED
)
def create_order(order_detail_in: OrderDetailCreate, db: Session = Depends(get_db)):  # noqa: B008
    return order_detail_service.create(db, obj_in=order_detail_in)


@router.patch("/{order_detail_id}", response_model=OrderDetailResponse)
def update_order(
    order_detail_id: int,
    order_detail_in: OrderDetailUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_detail_service.update(db, id=order_detail_id, obj_in=order_detail_in)


@router.delete("/{order_detail_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_detail_id: int, db: Session = Depends(get_db)):  # noqa: B008
    order_detail_service.remove(db, id=order_detail_id)
