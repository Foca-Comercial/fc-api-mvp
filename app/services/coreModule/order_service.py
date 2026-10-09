from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

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
    OrderSummaryResponse,
    OrderUpdate,
)
from app.services.base_service import BaseService
from app.utils.exceptions.business_exceptions import EntityNotFoundError


class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
    def __init__(self):
        super().__init__(repository=order_repository, entity_name="Pedido")

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

    def get_full_detail(self, db: Session, id_order: int) -> OrderFullDetailResponse:
        order = order_repository.get_order_with_full_relations(db, id_order)
        if not order:
            raise EntityNotFoundError("Pedido", id_order)

        if order.user_vehicle:
            person = order.user_vehicle.user_role.user.person
            driver_name = f"{person.name} {person.last_name}"

        items = [
            OrderDetailItemModal(
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

    def _validate_items(self, db: Session, items: list[OrderItemInput]) -> None:
        for item in items:
            self._ensure_reference(
                db,
                product_repository,
                item.id_product,
                field="id_product",
                label="Producto",
            )


order_service = OrderService()
