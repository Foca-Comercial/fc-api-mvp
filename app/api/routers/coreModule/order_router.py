from datetime import date

from fastapi import Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.api.routers.auth.secured_router import SecuredRouter
from app.db.database import get_db
from app.schemas.coreModule.order_schema import (
    OrderCreateExistingClient,
    OrderCreateNewClient,
    OrderFullDetailResponse,
    OrderItemsSyncRequest,
    OrderResponse,
    OrderSummaryResponse,
    OrderUpdate,
    OrderWithDetailsResponse,
)
from app.services.coreModule.order_service import order_service
from app.services.pdf.pdf_service import pdf_service
from app.utils.exceptions.business_exceptions import BusinessValidationError

router = SecuredRouter(prefix="/orders", tags=["Orders"])


@router.get("/", response_model=list[OrderResponse])
def get_all_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.get_all(db, skip=skip, limit=limit)


@router.get(
    "/dashboard-summary",
    response_model=list[OrderSummaryResponse],
    roles=["GESTOR_COMERCIAL"],
)
def get_dashboard_summary(
    target_date: date | None = Query(default_factory=date.today),  # type: ignore  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.get_dashboard_summary(db, target_date)  # type: ignore


@router.get(
    "/{id_order}/details",
    response_model=OrderFullDetailResponse,
    roles=["GESTOR_COMERCIAL"],
)
def get_order_full_detail(id_order: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.get_full_detail(db, id_order)


# Creacion de pedido para un cliente nuevo
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


# Creacion de pedido para un cliente existente
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


# Marcar un pedido como despachado
@router.post(
    "/{id_order}/dispatch",
    response_model=OrderResponse,
    roles=["GESTOR_COMERCIAL"],
)
def dispatch_order(id_order: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.dispatch_order(db, id_order)


# Generar CD
@router.get(
    "/{id_order}/receipt",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Devuelve el Comprobante de Despacho en formato PDF.",
        }
    },
    roles=["GESTOR_COMERCIAL", "SUBADMINISTRADOR"],
)
def get_dispatch_receipt(id_order: int, db: Session = Depends(get_db)):  # noqa: B008
    order = order_service.get(db, id_order)  # chequeo liviano, sin joins pesados
    if order.dispatch_time is None:
        raise BusinessValidationError(
            "El pedido aún no ha sido despachado; no hay comprobante para imprimir.",
            field="dispatch_time",
        )

    full_order = order_service.get_full_detail(db, id_order)
    pdf_bytes = pdf_service.generate_dispatch_receipt(full_order)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=CD_{full_order.purchase_order}.pdf"
        },
    )


# Marcar un pedido como entregado
@router.post(
    "/{id_order}/deliver",
    response_model=OrderResponse,
    roles=["GESTOR_COMERCIAL"],
)
def deliver_order(id_order: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.deliver_order(db, id_order)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.get(db, id=order_id)


# Actualiacion de Pedido (Quitar, Agregar, Modificar -> Productos)
@router.put(
    "/{order_id}/items-order",
    response_model=OrderWithDetailsResponse,
    roles=["GESTOR_COMERCIAL"],
)
def sync_order_items(
    order_id: int,
    body: OrderItemsSyncRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.sync_items(db, id_order=order_id, items=body.items)


@router.patch("/{order_id}", response_model=OrderResponse, roles=["GESTOR_COMERCIAL"])
def update_order(
    order_id: int,
    order_in: OrderUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.update(db, id=order_id, obj_in=order_in)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):  # noqa: B008
    order_service.remove(db, id=order_id)
