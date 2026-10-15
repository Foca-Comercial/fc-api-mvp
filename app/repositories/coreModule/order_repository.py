from datetime import date
from decimal import Decimal

from sqlalchemy import Date, case, cast, func, or_, select
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
from app.models.parametersModule.route import Route
from app.models.parametersModule.zone import Zone
from app.models.securityModule.person import Person
from app.models.securityModule.user import User
from app.models.securityModule.user_role import UserRole
from app.repositories.base_repository import BaseRepository
from app.repositories.time_filters import (
    between_bogota_dates,
    on_bogota_day,
    on_db_today,
)
from app.schemas.coreModule.order_history_schema import OrderHistoryFilters
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

    # Pedidos de HOY (día de Bogotá según la BD) generados desde la ruta, sin
    # cancelados: {id_client: id_order}. Evita generar dos veces la misma ruta.
    def get_route_orders_today(self, db: Session, id_route: int) -> dict[int, int]:
        stmt = select(Order.id_client, Order.id_order).where(
            Order.id_route == id_route,
            Order.state != OrderState.CANCELLED,
            on_db_today(Order.creation_datetime),
        )
        return {row.id_client: row.id_order for row in db.execute(stmt).all()}

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
                on_bogota_day(Order.creation_datetime, target_date),
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

    # ------------------------------------------------------------------
    # Vista Histórico
    # ------------------------------------------------------------------
    @staticmethod
    def _history_conditions(filters: OrderHistoryFilters) -> list:
        conditions = [
            between_bogota_dates(
                Order.creation_datetime, filters.date_from, filters.date_to
            )
        ]
        if filters.state is not None:
            conditions.append(Order.state == filters.state)
        if filters.id_route is not None:
            conditions.append(Order.id_route == filters.id_route)
        if filters.id_user_vehicle is not None:
            conditions.append(Order.id_user_vehicle == filters.id_user_vehicle)
        if filters.search:
            term = filters.search.strip()
            conditions.append(
                or_(Client.name.ilike(f"%{term}%"), Order.purchase_order == term)
            )
        return conditions

    # Cantidad de pedidos y ventas (sin cancelados) del filtro completo
    def get_history_totals(
        self, db: Session, filters: OrderHistoryFilters
    ) -> tuple[int, Decimal]:
        sales = func.coalesce(
            func.sum(
                case(
                    (Order.state != OrderState.CANCELLED, Order.order_total),
                    else_=0,
                )
            ),
            0,
        )
        stmt = (
            select(func.count(Order.id_order), sales)
            .join(Client, Client.id_client == Order.id_client)
            .where(*self._history_conditions(filters))
        )
        count, total = db.execute(stmt).one()
        return count, Decimal(total)

    # Una página del histórico, del más reciente al más antiguo
    def get_history_page(
        self, db: Session, filters: OrderHistoryFilters, *, offset: int, limit: int
    ) -> list[tuple]:
        # Productos agregados por pedido en una subconsulta: la paginación se
        # hace sobre pedidos, no sobre renglones de detalle.
        details = (
            select(
                OrderDetail.id_order,
                func.string_agg(Product.code, ", ").label("product_codes"),
                func.sum(OrderDetail.cant).label("total_quantity"),
            )
            .join(Product, Product.id_product == OrderDetail.id_product)
            .group_by(OrderDetail.id_order)
            .subquery()
        )
        created_local = func.timezone(BOGOTA_TZ.key, Order.creation_datetime)
        stmt = (
            select(
                Order.id_order,
                Order.purchase_order,
                cast(created_local, Date).label("order_date"),
                func.to_char(created_local, "HH24:MI").label("creation_time"),
                Client.name.label("client_name"),
                Zone.name.label("zone_name"),
                Route.name.label("route_name"),
                func.coalesce(details.c.product_codes, "").label("product_codes"),
                func.coalesce(details.c.total_quantity, 0).label("total_quantity"),
                Order.order_total,
                UserVehicle.code.label("driver_code"),
                (Person.name + " " + Person.last_name).label("driver_name"),
                Order.state,
            )
            .join(Client, Client.id_client == Order.id_client)
            .join(Neighborhood, Neighborhood.id_neighborhood == Client.id_neighborhood)
            .join(Zone, Zone.id_zone == Neighborhood.id_zone)
            .outerjoin(details, details.c.id_order == Order.id_order)
            .outerjoin(Route, Route.id_route == Order.id_route)
            .outerjoin(
                UserVehicle, UserVehicle.id_user_vehicle == Order.id_user_vehicle
            )
            .outerjoin(UserRole, UserRole.id_user_role == UserVehicle.id_user_role)
            .outerjoin(User, User.id_user == UserRole.id_user)
            .outerjoin(Person, Person.id_person == User.id_person)
            .where(*self._history_conditions(filters))
            .order_by(Order.creation_datetime.desc(), Order.id_order.desc())
            .offset(offset)
            .limit(limit)
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
