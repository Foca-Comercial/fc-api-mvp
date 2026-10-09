from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.timezone import BOGOTA_TZ
from app.models.coreModule.order import Order
from app.repositories.coreModule.client_repository import client_repository
from app.repositories.coreModule.order_detail_repository import order_detail_repository
from app.repositories.coreModule.order_repository import order_repository
from app.repositories.coreModule.product_repository import product_repository
from app.repositories.coreModule.user_vehicle_repository import user_vehicle_repository
from app.repositories.parametersModule.neighborhood_repository import (
    neighborhood_repository,
)
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
from app.services.base_service import BaseService
from app.services.validation import ReferenceRule
from app.utils.enums.order_state import OrderState
from app.utils.exceptions.business_exceptions import (
    BusinessRuleViolationError,
    BusinessValidationError,
    EntityNotFoundError,
)


class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
    references = (
        ReferenceRule("id_user_vehicle", "Vehículo", user_vehicle_repository),
    )

    def __init__(self):
        super().__init__(repository=order_repository, entity_name="Pedido")

    # Obtiene todos los pedidos del dia
    def get_dashboard_summary(
        self, db: Session, target_date: date
    ) -> list[OrderSummaryResponse]:
        rows = order_repository.get_daily_summary(db, target_date)

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

        if order.user_vehicle:
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
            driver_code=order.user_vehicle.code,  # type: ignore
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
        self._validate_items(db, obj_in.items)
        return self._create_order_with_items(
            db, id_client=obj_in.id_client, id_user_taker=id_user_taker, order_in=obj_in
        )

    # Creacion de pedido directa a OrderDetail
    def _create_order_with_items(
        self, db: Session, *, id_client, id_user_taker, order_in
    ) -> Order:
        if order_in.id_user_vehicle is not None:
            self._ensure_reference(
                db,
                user_vehicle_repository,
                order_in.id_user_vehicle,
                field="id_user_vehicle",
                label="Vehículo",
            )

        order = order_repository.add(
            db,
            obj_in_data={
                "purchase_order": order_in.purchase_order,
                "estimated_delivery": order_in.estimated_delivery,
                "id_client": id_client,
                "id_user_vehicle": order_in.id_user_vehicle,
                "id_user_taker": id_user_taker,
            },
        )

        total = Decimal(0)
        for item in order_in.items:
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
        db.commit()
        db.refresh(order)
        return order

    def dispatch_order(self, db: Session, id_order: int) -> Order:
        order = self.get(db, id_order)

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

    def _validate_items(self, db: Session, items: list[OrderItemInput]) -> None:
        for item in items:
            self._ensure_reference(
                db,
                product_repository,
                item.id_product,
                field="id_product",
                label="Producto",
            )

    # Actualiacion de Pedido (Quitar, Agregar, Modificar -> Productos)
    def sync_items(
        self, db: Session, *, id_order: int, items: list[OrderItemSync]
    ) -> Order:
        order = self.get(db, id_order)  # 404 si no existe

        if order.state != OrderState.PENDING:
            raise BusinessRuleViolationError(
                f"No se pueden modificar los productos de un pedido en estado "
                f"'{order.state.value}'. Solo se permite mientras está 'PENDING'."
            )

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


order_service = OrderService()
