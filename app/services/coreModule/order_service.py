from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.timezone import BOGOTA_TZ
from app.models.coreModule.order import Order
from app.repositories.coreModule.client_repository import client_repository
from app.repositories.coreModule.order_detail_repository import order_detail_repository
from app.repositories.coreModule.order_repository import order_repository
from app.repositories.coreModule.product_repository import product_repository
from app.repositories.coreModule.special_customer_price_repository import (
    special_customer_price_repository,
)
from app.repositories.coreModule.user_vehicle_repository import user_vehicle_repository
from app.repositories.parametersModule.neighborhood_repository import (
    neighborhood_repository,
)
from app.repositories.parametersModule.route_repository import route_repository
from app.schemas.coreModule.order_schema import (
    OrderCreate,
    OrderCreateExistingClient,
    OrderCreateNewClient,
    OrderDetailItemModal,
    OrderFullDetailResponse,
    OrderItemInput,
    OrderItemSync,
    OrderSummaryResponse,
    OrderUpdate,
)
from app.schemas.coreModule.route_order_schema import (
    RouteOfDayResponse,
    RouteOrdersCreate,
    RouteOrderTemplateResponse,
    RouteTemplateClient,
    RouteTemplatePrice,
    RouteTemplateProduct,
)
from app.services.base_service import BaseService
from app.services.validation import ReferenceRule
from app.utils.enums.order_state import OrderState
from app.utils.exceptions.business_exceptions import (
    BusinessError,
    BusinessRuleViolationError,
    BusinessValidationError,
    ConflictError,
    EntityNotFoundError,
)

# purchase_order es String(3): consecutivo diario de 001 a 999
MAX_DAILY_ORDERS = 999


class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
    references = (
        ReferenceRule("id_user_vehicle", "Vehículo", user_vehicle_repository),
    )

    def __init__(self):
        super().__init__(repository=order_repository, entity_name="Pedido")

    # Tabla principal: pedidos del día en PENDING y CANCELLED
    def get_dashboard_summary(
        self, db: Session, target_date: date
    ) -> list[OrderSummaryResponse]:
        return self._to_summary(order_repository.get_daily_summary(db, target_date))

    # Vista de despachados: pedidos del día en DISPATCHED y DELIVERED
    def get_dispatched_summary(
        self, db: Session, target_date: date
    ) -> list[OrderSummaryResponse]:
        return self._to_summary(
            order_repository.get_dispatched_summary(db, target_date)
        )

    @staticmethod
    def _to_summary(rows: list) -> list[OrderSummaryResponse]:
        return [
            OrderSummaryResponse(
                id_order=row.id_order,  # type: ignore
                purchase_order=row.purchase_order,  # type: ignore
                creation_time=row.creation_time,  # type: ignore
                client_name=row.client_name,  # type: ignore
                zone_name=row.zone_name,  # type: ignore
                product_codes=row.product_codes,  # type: ignore
                total_quantity=row.total_quantity,  # type: ignore
                driver_code=row.driver_code,  # type: ignore
                driver_name=row.driver_name,  # type: ignore
                state=row.state,  # type: ignore
            )
            for row in rows
        ]

    # Obtiene los detalles de un pedido
    def get_full_detail(self, db: Session, id_order: int) -> OrderFullDetailResponse:
        order = order_repository.get_order_with_full_relations(db, id_order)
        if not order:
            raise EntityNotFoundError("Pedido", id_order)

        # El conductor es opcional: un pedido puede despacharse sin asignar
        driver_code: str | None = None
        driver_name: str | None = None
        if order.user_vehicle:
            driver_code = order.user_vehicle.code
            person = order.user_vehicle.user_role.user.person
            driver_name = f"{person.name} {person.last_name}"

        items = [
            OrderDetailItemModal(
                id_order_detail=detail.id_order_detail,
                id_product=detail.id_product,
                product_code=detail.product.code,
                product_name=detail.product.name,
                cant=detail.cant,
                unit_price=detail.unit_price,
                subtotal=detail.subtotal,
            )
            for detail in order.order_details
        ]

        return OrderFullDetailResponse(
            id_order=order.id_order,
            purchase_order=order.purchase_order,
            creation_datetime=order.creation_datetime,
            estimated_delivery=order.estimated_delivery,
            dispatch_time=order.dispatch_time,
            state=order.state,
            order_total=order.order_total,  # type: ignore
            client_name=order.client.name,
            client_phone=order.client.phone,
            client_address=order.client.address,
            neighborhood_name=order.client.neighborhood.name,
            zone_name=order.client.neighborhood.zone.name,
            driver_code=driver_code,
            driver_name=driver_name,
            items=items,
        )

    # Creacion de pedido para un cliente nuevo
    def create_for_new_client(
        self, db: Session, *, obj_in: OrderCreateNewClient, id_user_taker: int
    ) -> Order:
        self._ensure_reference(
            db,
            neighborhood_repository,
            obj_in.client.id_neighborhood,
            field="id_neighborhood",
            label="Barrio",
        )
        self._validate_items(db, obj_in.items)

        client = client_repository.add(
            db, obj_in_data={**obj_in.client.model_dump(), "is_registered": False}
        )
        return self._create_order_with_items(
            db, id_client=client.id_client, id_user_taker=id_user_taker, order_in=obj_in
        )

    # Creacion de pedido para un cliente existente
    def create_for_existing_client(
        self, db: Session, *, obj_in: OrderCreateExistingClient, id_user_taker: int
    ) -> Order:
        self._ensure_reference(
            db, client_repository, obj_in.id_client, field="id_client", label="Cliente"
        )
        if not client_repository.get(db, obj_in.id_client).is_registered:  # type: ignore
            raise BusinessValidationError(
                "Solo se pueden tomar pedidos de clientes registrados en este flujo.",
                field="id_client",
                code="CLIENT_NOT_REGISTERED",
            )
        self._validate_items(db, obj_in.items)
        return self._create_order_with_items(
            db, id_client=obj_in.id_client, id_user_taker=id_user_taker, order_in=obj_in
        )

    # Creacion de pedido directa a OrderDetail (un pedido, con commit)
    def _create_order_with_items(
        self, db: Session, *, id_client, id_user_taker, order_in
    ) -> Order:
        if order_in.id_user_vehicle is not None:
            self._ensure_vehicle(db, order_in.id_user_vehicle)

        order = self._add_order_with_items(
            db,
            id_client=id_client,
            id_user_taker=id_user_taker,
            items=order_in.items,
            estimated_delivery=order_in.estimated_delivery,
            id_user_vehicle=order_in.id_user_vehicle,
        )
        db.commit()
        db.refresh(order)
        return order

    def _ensure_vehicle(self, db: Session, id_user_vehicle: int) -> None:
        self._ensure_reference(
            db,
            user_vehicle_repository,
            id_user_vehicle,
            field="id_user_vehicle",
            label="Vehículo",
        )

    # Inserta pedido + detalles SIN commit (flush): lo usan la creación
    # individual y la creación en lote por ruta, que confirma todo al final.
    def _add_order_with_items(
        self,
        db: Session,
        *,
        id_client: int,
        id_user_taker: int,
        items: list[OrderItemInput],
        estimated_delivery=None,
        id_user_vehicle: int | None = None,
        id_route: int | None = None,
    ) -> Order:
        order = order_repository.add(
            db,
            obj_in_data={
                "purchase_order": self._next_purchase_order(db),
                "estimated_delivery": estimated_delivery,
                "id_client": id_client,
                "id_user_vehicle": id_user_vehicle,
                "id_user_taker": id_user_taker,
                "id_route": id_route,
            },
        )

        total = Decimal(0)
        for item in items:
            subtotal = item.unit_price * item.cant
            order_detail_repository.add(
                db,
                obj_in_data={
                    "id_order": order.id_order,
                    "id_product": item.id_product,
                    "cant": item.cant,
                    "unit_price": item.unit_price,
                    "subtotal": subtotal,
                },
            )
            total += subtotal

        order.order_total = total
        db.add(order)
        db.flush()
        return order

    # ------------------------------------------------------------------
    # Pedidos por ruta
    # ------------------------------------------------------------------

    # Rutas activas que salen ese día de la semana
    def get_routes_of_day(
        self, db: Session, target_date: date
    ) -> list[RouteOfDayResponse]:
        rows = route_repository.get_routes_of_day(
            db, target_date.isoweekday(), target_date
        )
        return [
            RouteOfDayResponse(
                id_route=route.id_route,
                name=route.name,
                departure_time=route.departure_time,
                days_week=route.days_week,
                clients_count=clients_count,
                orders_count=orders_count,
            )
            for route, clients_count, orders_count in rows
        ]

    # Precarga: clientes de la ruta con el precio que aplica a cada producto
    def get_route_template(
        self, db: Session, id_route: int
    ) -> RouteOrderTemplateResponse:
        route = route_repository.get(db, id_route)
        if route is None:
            raise EntityNotFoundError("Ruta", id_route)

        products = [p for p, _ in product_repository.get_catalog(db)]
        clients = route_repository.get_orderable_clients(db, id_route)
        specials = special_customer_price_repository.get_for_clients(
            db,
            [c.id_client for c in clients],  # type: ignore
        )
        existing = order_repository.get_route_orders_today(db, id_route)

        return RouteOrderTemplateResponse(
            id_route=route.id_route,
            name=route.name,
            departure_time=route.departure_time,
            products=[
                RouteTemplateProduct(
                    id_product=p.id_product,
                    code=p.code,
                    name=p.name,
                    base_price=p.base_price,
                )
                for p in products
            ],
            clients=[
                RouteTemplateClient(
                    id_client=c.id_client,  # type: ignore
                    name=c.name,  # type: ignore
                    phone=c.phone,  # type: ignore
                    address=c.address,  # type: ignore
                    neighborhood_name=c.neighborhood_name,  # type: ignore
                    zone_name=c.zone_name,  # type: ignore
                    prices=[
                        RouteTemplatePrice(
                            id_product=p.id_product,
                            unit_price=specials.get(
                                (c.id_client, p.id_product),  # type: ignore
                                p.base_price,  # type: ignore
                            ),  # type: ignore
                            is_special=(c.id_client, p.id_product) in specials,  # type: ignore
                        )
                        for p in products
                    ],
                    existing_order_id=existing.get(c.id_client),  # type: ignore
                )
                for c in clients
            ],
        )

    # Crea en UNA transacción los pedidos de los clientes de la ruta que vienen
    # con productos. Si cualquiera falla, no se crea ninguno.
    def create_for_route(
        self,
        db: Session,
        *,
        id_route: int,
        obj_in: RouteOrdersCreate,
        id_user_taker: int,
    ) -> list[Order]:
        # Bloquea la ruta: dos gestores generando la misma ruta a la vez no
        # pueden duplicar pedidos (el segundo espera y ve los del primero).
        route = route_repository.get_for_update(db, id_route)
        if route is None:
            raise EntityNotFoundError("Ruta", id_route)
        if not route.active:
            raise BusinessValidationError(
                "La ruta está inactiva.", field="id_route", code="ROUTE_INACTIVE"
            )

        client_ids = [o.id_client for o in obj_in.orders]
        repeated = sorted({i for i in client_ids if client_ids.count(i) > 1})
        if repeated:
            raise BusinessValidationError(
                f"Cliente repetido en la lista (ID: {_ids(repeated)}).",
                field="id_client",
                code="DUPLICATE_CLIENT",
            )

        orderable = {
            c.id_client  # type: ignore
            for c in route_repository.get_orderable_clients(db, id_route)  # type: ignore
        }
        outside = [i for i in client_ids if i not in orderable]
        if outside:
            raise BusinessValidationError(
                "Estos clientes no están asignados a la ruta o no están activos "
                f"(ID: {_ids(outside)}).",
                field="id_client",
                code="CLIENT_NOT_IN_ROUTE",
            )

        existing = order_repository.get_route_orders_today(db, id_route)
        already = [i for i in client_ids if i in existing]
        if already:
            raise ConflictError(
                "Estos clientes ya tienen pedido de hoy desde esta ruta "
                f"(ID: {_ids(already)}). Edítalo en lugar de crear otro.",
                field="id_client",
                code="ROUTE_ORDER_EXISTS",
            )

        if obj_in.id_user_vehicle is not None:
            self._ensure_vehicle(db, obj_in.id_user_vehicle)

        for client_order in obj_in.orders:
            try:
                self._validate_items(db, client_order.items)
            except BusinessError as error:
                # Indica a qué cliente pertenece el renglón con error
                raise BusinessValidationError(
                    f"Cliente {client_order.id_client}: {error.message}",
                    field=error.field,
                    code=error.code,
                ) from error

        orders = [
            self._add_order_with_items(
                db,
                id_client=client_order.id_client,
                id_user_taker=id_user_taker,
                items=client_order.items,
                estimated_delivery=obj_in.estimated_delivery,
                id_user_vehicle=obj_in.id_user_vehicle,
                id_route=id_route,
            )
            for client_order in obj_in.orders
        ]
        db.commit()
        for order in orders:
            db.refresh(order)
        return orders

    # Consecutivo del día ("001", "002", ...). Lo asigna el servidor, nunca el
    # cliente; los pedidos de días anteriores conservan el número que recibieron.
    def _next_purchase_order(self, db: Session) -> str:
        number = order_repository.next_daily_number(db)
        if number > MAX_DAILY_ORDERS:
            # La excepción revierte la transacción, incluido el incremento
            raise BusinessRuleViolationError(
                f"Se alcanzó el máximo de {MAX_DAILY_ORDERS} pedidos del día.",
                rule_code="DAILY_ORDER_LIMIT",
            )
        return f"{number:03d}"

    # Marcar pdido como despachado
    def dispatch_order(self, db: Session, id_order: int) -> Order:
        order = self.get_for_update(db, id_order)

        if order.state != OrderState.PENDING:
            raise BusinessValidationError(
                f"Solo se pueden despachar pedidos en estado 'PENDING'. "
                f"Estado actual: '{order.state.value}'.",
                field="state",
            )

        order.state = OrderState.DISPATCHED
        order.dispatch_time = datetime.now(BOGOTA_TZ).time()

        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    # Marcar pdido como entregado
    def deliver_order(self, db: Session, id_order: int) -> Order:
        order = self.get_for_update(db, id_order)

        if order.state != OrderState.DISPATCHED:
            raise BusinessValidationError(
                f"Solo se pueden marcar como entregados los pedidos en estado "
                f"'DISPATCHED'. Estado actual: '{order.state.value}'.",
                field="state",
            )

        order.state = OrderState.DELIVERED
        order.delivery_time = datetime.now(BOGOTA_TZ).time()

        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    def _validate_items(self, db: Session, items: list[OrderItemInput]) -> None:
        self._ensure_no_duplicate_products(items)
        for item in items:
            self._ensure_reference(
                db,
                product_repository,
                item.id_product,
                field="id_product",
                label="Producto",
            )

    @staticmethod
    def _ensure_no_duplicate_products(
        items: list[OrderItemInput] | list[OrderItemSync],
    ) -> None:
        """Un producto solo puede aparecer en un renglón del pedido."""
        seen: set[int] = set()
        duplicated: list[int] = []
        for item in items:
            if item.id_product in seen and item.id_product not in duplicated:
                duplicated.append(item.id_product)
            seen.add(item.id_product)
        if duplicated:
            ids = ", ".join(str(i) for i in duplicated)
            raise BusinessValidationError(
                f"Producto repetido en el pedido (ID: {ids}). "
                "Agrupa la cantidad en un solo renglón.",
                field="id_product",
                code="DUPLICATE_PRODUCT",
            )

    # Actualiacion de Pedido (Quitar, Agregar, Modificar -> Productos)
    def sync_items(
        self, db: Session, *, id_order: int, items: list[OrderItemSync]
    ) -> Order:
        order = self.get_for_update(db, id_order)  # 404 si no existe; bloquea la fila

        if order.state != OrderState.PENDING:
            raise BusinessRuleViolationError(
                f"No se pueden modificar los productos de un pedido en estado "
                f"'{order.state.value}'. Solo se permite mientras está 'PENDING'."
            )

        # Antes de tocar nada: la lista final no puede repetir productos
        self._ensure_no_duplicate_products(items)

        existing_details = {d.id_order_detail: d for d in order.order_details}
        incoming_ids = {
            i.id_order_detail for i in items if i.id_order_detail is not None
        }

        # Validar que todo id_order_detail enviado exista y pertenezca a ESTE pedido
        for item in items:
            if (
                item.id_order_detail is not None
                and item.id_order_detail not in existing_details
            ):
                raise BusinessValidationError(
                    f"El detalle {item.id_order_detail} no pertenece a este pedido.",
                    field="id_order_detail",
                )

        # Eliminar los que ya no vienen en la lista
        for detail_id, detail in existing_details.items():
            if detail_id not in incoming_ids:
                order.order_details.remove(detail)
                db.delete(detail)

        total = Decimal("0")  # noqa: FURB157
        for item in items:
            self._ensure_reference(
                db,
                product_repository,
                item.id_product,
                field="id_product",
                label="Producto",
            )
            subtotal = item.unit_price * item.cant

            if item.id_order_detail is not None:
                detail = existing_details[item.id_order_detail]
                detail.id_product = item.id_product
                detail.cant = item.cant
                detail.unit_price = item.unit_price
                detail.subtotal = subtotal
                db.add(detail)
            else:
                order_detail_repository.add(
                    db,
                    obj_in_data={
                        "id_order": order.id_order,
                        "id_product": item.id_product,
                        "cant": item.cant,
                        "unit_price": item.unit_price,
                        "subtotal": subtotal,
                    },
                )
            total += subtotal

        order.order_total = total
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    _FINAL_STATES = (OrderState.DELIVERED, OrderState.CANCELLED)

    # PATCH (reasignar conductor): mismo flujo que BaseService.update, pero
    # bloqueando la fila, porque la validación depende del estado del pedido.
    def update(self, db: Session, *, id: int, obj_in: OrderUpdate) -> Order:
        db_obj = self.get_for_update(db, id)
        self._validate_before_update(db, obj_in, db_obj)
        return self.repository.update(db, db_obj=db_obj, obj_in=obj_in)

    def _validate_before_update(
        self, db: Session, obj_in: OrderUpdate, existing: Order
    ) -> None:
        super()._validate_before_update(db, obj_in, existing)
        if existing.state in self._FINAL_STATES:
            raise BusinessValidationError(
                f"No se puede reasignar el conductor de un pedido en estado "
                f"'{existing.state.value}'.",
                field="id_user_vehicle",
            )


def _ids(values: list[int]) -> str:
    return ", ".join(str(v) for v in values)


order_service = OrderService()
