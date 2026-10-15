from datetime import date

from sqlalchemy import Date, cast, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from app.core.timezone import BOGOTA_TZ
from app.models.coreModule.client import Client
from app.models.coreModule.daily_order_counter import DailyOrderCounter
from app.models.coreModule.order import Order
from app.models.coreModule.order_detail import OrderDetail
from app.models.coreModule.product import Product
from app.models.coreModule.user_vehicle import UserVehicle
from app.models.parametersModule.neighborhood import Neighborhood
from app.models.parametersModule.zone import Zone
from app.models.securityModule.person import Person
from app.models.securityModule.user import User
from app.models.securityModule.user_role import UserRole
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.order_schema import OrderCreate, OrderUpdate
from app.utils.enums.order_state import OrderState


class RepositoryOrder(BaseRepository[Order, OrderCreate, OrderUpdate]):
    # Siguiente consecutivo del día (hora de Bogotá). Debe llamarse dentro de la
    # misma transacción que inserta el pedido: bloquea la fila del día hasta el
    # commit y se revierte junto con él.
    def next_daily_number(self, db: Session) -> int:
        # now() es la hora de inicio de la transacción: el mismo instante que
        # recibirá creation_datetime (server_default), así el día coincide.
        today = cast(func.timezone(BOGOTA_TZ.key, func.now()), Date)
        stmt = (
            insert(DailyOrderCounter)
            .values(counter_date=today, last_value=1)
            .on_conflict_do_update(
                index_elements=[DailyOrderCounter.counter_date],
                set_={"last_value": DailyOrderCounter.last_value + 1},
            )
            .returning(DailyOrderCounter.last_value)
        )
        return db.scalar(stmt)  # type: ignore

    # Tabla principal: pedidos del día por gestionar (pendientes y cancelados)
    def get_daily_summary(self, db: Session, target_date: date) -> list[tuple]:
        return self._summary_by_states(
            db, target_date, (OrderState.PENDING, OrderState.CANCELLED)
        )

    # Vista de despachados: pedidos del día que ya salieron (despachados y entregados)
    def get_dispatched_summary(self, db: Session, target_date: date) -> list[tuple]:
        return self._summary_by_states(
            db, target_date, (OrderState.DISPATCHED, OrderState.DELIVERED)
        )

    def _summary_by_states(
        self, db: Session, target_date: date, states: tuple[OrderState, ...]
    ) -> list[tuple]:
        # creation_datetime es TIMESTAMPTZ: se convierte a hora local de Bogotá
        # antes de extraer fecha/hora, sin depender de la zona de la sesión.
        created_local = func.timezone(BOGOTA_TZ.key, Order.creation_datetime)
        stmt = (
            select(
                Order.id_order,
                Order.purchase_order,
                func.to_char(created_local, "HH24:MI").label("creation_time"),
                Client.name.label("client_name"),
                Zone.name.label("zone_name"),
                func.string_agg(Product.code, ", ").label("product_codes"),
                func.sum(OrderDetail.cant).label("total_quantity"),
                Order.state,
                UserVehicle.code.label("driver_code"),
                (Person.name + " " + Person.last_name).label(
                    "driver_name"
                ),  # Nombre concatenado separado del código
            )
            .join(Client, Order.id_client == Client.id_client)
            .join(Neighborhood, Client.id_neighborhood == Neighborhood.id_neighborhood)
            .join(Zone, Neighborhood.id_zone == Zone.id_zone)
            .join(OrderDetail, Order.id_order == OrderDetail.id_order)
            .join(Product, OrderDetail.id_product == Product.id_product)
            .outerjoin(
                UserVehicle, Order.id_user_vehicle == UserVehicle.id_user_vehicle
            )
            .outerjoin(UserRole, UserVehicle.id_user_role == UserRole.id_user_role)
            .outerjoin(User, UserRole.id_user == User.id_user)
            .outerjoin(Person, User.id_person == Person.id_person)
            .where(
                # 1. Filtrar solo los del día indicado (por defecto hoy)
                func.date(created_local) == target_date,
                # 2. Solo los estados que corresponden a la vista
                Order.state.in_(states),
            )
            .group_by(
                Order.id_order,
                Client.name,
                Zone.name,
                UserVehicle.code,
                Person.name,
                Person.last_name,
            )
            # 3. Ordenar ascendente: el más antiguo arriba, el último registrado al final
            .order_by(Order.creation_datetime.asc())
        )
        return list(db.execute(stmt).all())

    # Obtiene los detalles de un pedido
    def get_order_with_full_relations(self, db: Session, id_order: int) -> Order | None:
        stmt = (
            select(Order)
            .options(
                joinedload(Order.client)
                .joinedload(Client.neighborhood)
                .joinedload(Neighborhood.zone),
                joinedload(Order.order_details).joinedload(OrderDetail.product),
                joinedload(Order.user_vehicle)
                .joinedload(UserVehicle.user_role)
                .joinedload(UserRole.user)
                .joinedload(User.person),
            )
            .where(Order.id_order == id_order)
        )
        return db.scalar(stmt)


# Intancia del repositorio inyectando el modelo ORM
order_repository = RepositoryOrder(Order)
