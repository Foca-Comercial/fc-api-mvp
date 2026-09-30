from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.coreModule.order_schema import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
)
from app.services.coreModule.order_service import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/", response_model=list[OrderResponse])
def get_all_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.get_all(db, skip=skip, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.get(db, id=order_id)


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.create(db, obj_in=order_in)


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    order_in: OrderUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.update(db, id=order_id, obj_in=order_in)


@router.delete("/{order_id}", response_model=OrderResponse)
def delete_order(order_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.remove(db, id=order_id)
