from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.order_schema import (
    OrderCreateExistingClient,
    OrderCreateNewClient,
    OrderResponse,
    OrderUpdate,
    OrderWithDetailsResponse,
)
from app.services.coreModule.order_service import order_service

router = SecuredRouter(prefix="/orders", tags=["Orders"])


@router.get("/", response_model=list[OrderResponse])
def get_all_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.get_all(db, skip=skip, limit=limit)


@router.post(
    "/new-client",
    response_model=OrderWithDetailsResponse,
    status_code=status.HTTP_201_CREATED,
    roles=["GESTOR_COMERCIAL"],
)
def create_order_new_client(
    order_in: OrderCreateNewClient,
    db: Session = Depends(get_db),  # noqa: B008
    current: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    return order_service.create_for_new_client(
        db, obj_in=order_in, id_user_taker=current.user.id_user
    )


@router.post(
    "/existing-client",
    response_model=OrderWithDetailsResponse,
    status_code=status.HTTP_201_CREATED,
    roles=["GESTOR_COMERCIAL"],
)
def create_order_existing_client(
    order_in: OrderCreateExistingClient,
    db: Session = Depends(get_db),  # noqa: B008
    current: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    return order_service.create_for_existing_client(
        db, obj_in=order_in, id_user_taker=current.user.id_user
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.get(db, id=order_id)


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    order_in: OrderUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.update(db, id=order_id, obj_in=order_in)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):  # noqa: B008
    order_service.remove(db, id=order_id)
