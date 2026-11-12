from datetime import date

from fastapi import Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.api.routers.auth.secured_router import SecuredRouter
from app.core.timezone import today_bogota
from app.db.database import get_db
from app.schemas.common.page_schema import SortDirection
from app.schemas.coreModule.order_history_schema import OrderHistoryPage
from app.schemas.coreModule.order_schema import (
    OrderCancelRequest,
    OrderCreateExistingClient,
    OrderCreateNewClient,
    OrderDispatchBatchRequest,
    OrderDispatchBatchResponse,
    OrderFullDetailResponse,
    OrderItemsSyncRequest,
    OrderResponse,
    OrderSummaryResponse,
    OrderUpdate,
    OrderWithDetailsResponse,
)
from app.schemas.coreModule.route_order_schema import (
    RouteOfDayResponse,
    RouteOrdersCreate,
    RouteOrdersCreatedResponse,
    RouteOrderTemplateResponse,
)
from app.services.coreModule.order_service import order_service
from app.services.pdf.pdf_service import pdf_service
from app.utils.enums.invoice_type import InvoiceType
from app.utils.enums.order_state import OrderState
from app.utils.enums.payment_method import PaymentMethod
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
    target_date: date | None = Query(default_factory=today_bogota),  # type: ignore  # noqa: B008
    id_route: int | None = Query(None, gt=0),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.get_dashboard_summary(db, target_date, id_route)  # type: ignore


@router.get(
    "/dispatched-summary",
    response_model=list[OrderSummaryResponse],
    roles=["GESTOR_COMERCIAL"],
)
def get_dispatched_summary(
    target_date: date | None = Query(default_factory=today_bogota),  # type: ignore  # noqa: B008
    id_route: int | None = Query(None, gt=0),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.get_dispatched_summary(db, target_date, id_route)  # type: ignore


# -----------------------------------------------------
# Vista Histórico (literal: antes de /{order_id})
# -----------------------------------------------------
@router.get(
    "/history",
    response_model=OrderHistoryPage,
    roles=["GESTOR_COMERCIAL"],
)
def get_order_history(
    date_from: date | None = Query(None, description="Por defecto: 1 del mes anterior"),  # noqa: B008
    date_to: date | None = Query(None, description="Por defecto: hoy (Bogotá)"),  # noqa: B008
    state: OrderState | None = None,
    id_route: int | None = Query(None, gt=0),
    id_user_vehicle: int | None = Query(None, gt=0),
    search: str | None = Query(
        None, min_length=1, description="Nombre del cliente o N.° de pedido exacto"
    ),
    payment_method: PaymentMethod | None = None,
    invoice_type: InvoiceType | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str | None = Query(
        None,
        max_length=40,
        pattern=r"^[a-z_]+$",
        description="date (por defecto), purchase_order, client_name, zone_name, "
        "route_name, total_quantity, total, driver_name, state, payment_method, "
        "invoice_type",
    ),
    sort_dir: SortDirection = Query(
        "asc", description="asc (por defecto: del más antiguo al más nuevo) o desc"
    ),
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.get_history(
        db,
        date_from=date_from,
        date_to=date_to,
        state=state,
        id_route=id_route,
        id_user_vehicle=id_user_vehicle,
        search=search,
        page=page,
        page_size=page_size,
        payment_method=payment_method,
        invoice_type=invoice_type,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


# -----------------------------------------------------
# Pedidos por ruta (literales: antes de /{order_id})
# -----------------------------------------------------
@router.get(
    "/routes-of-day",
    response_model=list[RouteOfDayResponse],
    roles=["GESTOR_COMERCIAL"],
)
def get_routes_of_day(
    target_date: date | None = Query(default_factory=today_bogota),  # type: ignore  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.get_routes_of_day(db, target_date)  # type: ignore


@router.get(
    "/routes/{id_route}/template",
    response_model=RouteOrderTemplateResponse,
    roles=["GESTOR_COMERCIAL"],
)
def get_route_order_template(id_route: int, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.get_route_template(db, id_route)


@router.post(
    "/routes/{id_route}",
    response_model=RouteOrdersCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    roles=["GESTOR_COMERCIAL"],
)
def create_route_orders(
    id_route: int,
    body: RouteOrdersCreate,
    db: Session = Depends(get_db),  # noqa: B008
    current: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    orders = order_service.create_for_route(
        db, id_route=id_route, obj_in=body, id_user_taker=current.user.id_user
    )
    return RouteOrdersCreatedResponse(
        id_route=id_route,
        created=len(orders),
        orders=[OrderResponse.model_validate(o) for o in orders],
    )


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


# Despachar varios pedidos a la vez (todo o nada)
@router.post(
    "/dispatch-batch",
    response_model=OrderDispatchBatchResponse,
    roles=["GESTOR_COMERCIAL"],
)
def dispatch_orders_batch(
    body: OrderDispatchBatchRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    orders = order_service.dispatch_batch(db, body.ids)
    return OrderDispatchBatchResponse(
        dispatched=len(orders),
        orders=[OrderResponse.model_validate(o) for o in orders],
    )


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
    roles=["GESTOR_COMERCIAL"],
)
def get_dispatch_receipt(id_order: int, db: Session = Depends(get_db)):  # noqa: B008
    order = order_service.get(db, id_order)  # chequeo liviano, sin joins pesados
    if not order.has_receipt:
        raise BusinessValidationError(
            "Este pedido no lleva comprobante de despacho: solo los pedidos POS en "
            "efectivo lo tienen.",
            field="payment_method",
            code="RECEIPT_NOT_AVAILABLE",
        )
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


# Cancelar un pedido con motivo (queda registrado quién y cuándo)
@router.post(
    "/{id_order}/cancel",
    response_model=OrderResponse,
    roles=["GESTOR_COMERCIAL"],
)
def cancel_order(
    id_order: int,
    body: OrderCancelRequest,
    db: Session = Depends(get_db),  # noqa: B008
    current: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    return order_service.cancel_order(
        db, id_order, body, id_user=current.user.id_user
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
    current: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    # Quien edita queda registrado como el último que cambió los productos
    return order_service.sync_items(
        db, id_order=order_id, items=body.items, id_user=current.user.id_user
    )


@router.patch("/{order_id}", response_model=OrderResponse, roles=["GESTOR_COMERCIAL"])
def update_order(
    order_id: int,
    order_in: OrderUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.update(db, id=order_id, obj_in=order_in)


# Sin DELETE: un pedido no se elimina, se cancela (POST /{id_order}/cancel).
