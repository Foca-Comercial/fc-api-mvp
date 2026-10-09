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
    OrderItemInput,
    OrderUpdate,
)
from app.services.base_service import BaseService


class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
    def __init__(self):
        super().__init__(repository=order_repository, entity_name="Pedido")

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
