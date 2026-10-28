from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.timezone import bogota_month_range
from app.models.coreModule.order import Order
from app.models.coreModule.order_detail import OrderDetail
from app.models.coreModule.shift_closure import ShiftClosure
from app.repositories.base_repository import BaseRepository
from app.repositories.coreModule.order_repository import BILLABLE_STATES
from app.schemas.coreModule.shift_closure_schema import (
    ShiftClosureCreate,
    ShiftClosureUpdate,
)


class RepositoryShiftClosure(
    BaseRepository[ShiftClosure, ShiftClosureCreate, ShiftClosureUpdate]
):
    # Cierres guardados de un día: {id_user_vehicle: ShiftClosure}.
    # populate_existing: la exportación los escribe con SQL directo (upsert),
    # así que los objetos que ya estuvieran en la sesión se refrescan.
    def get_by_date(self, db: Session, day: date) -> dict[int, ShiftClosure]:
        stmt = (
            select(ShiftClosure)
            .where(ShiftClosure.closure_date == day)
            .execution_options(populate_existing=True)
        )
        return {c.id_user_vehicle: c for c in db.scalars(stmt).all()}

    # Registra la exportación del día: un cierre por vendedor (insert o update
    # sobre uq_shift_closure_date_vehicle) y elimina los cierres de vendedores
    # que ya no tienen pedidos facturables ese día (p. ej. se les reasignaron).
    # totals: [(id_user_vehicle, total_orders, total_sales)]
    def save_exported(
        self, db: Session, day: date, totals: Sequence[tuple[int, int, Decimal]]
    ) -> None:
        ids = [id_user_vehicle for id_user_vehicle, _, _ in totals]
        db.execute(
            delete(ShiftClosure).where(
                ShiftClosure.closure_date == day,
                ShiftClosure.id_user_vehicle.not_in(ids),
            )
        )
        if not totals:
            return
        stmt = insert(ShiftClosure).values(
            [
                {
                    "closure_date": day,
                    "id_user_vehicle": id_user_vehicle,
                    "total_orders": orders,
                    "total_sales": sales,
                    "exported_siigo": True,
                    "exported_at": func.now(),
                }
                for id_user_vehicle, orders, sales in totals
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_shift_closure_date_vehicle",
            set_={
                "total_orders": stmt.excluded.total_orders,
                "total_sales": stmt.excluded.total_sales,
                "exported_siigo": True,
                "exported_at": stmt.excluded.exported_at,
            },
        )
        db.execute(stmt)

    # Días del mes con pedidos facturables cuyo cierre no está exportado o quedó
    # desactualizado: la cantidad de pedidos o el total exportados (sumando
    # todos los vendedores del día) no coinciden con los pedidos actuales.
    def get_unclosed_days(self, db: Session, month: date) -> list[date]:
        start, end = bogota_month_range(month.year, month.month)
        order_day = Order.delivery_date
        billable = (
            select(
                order_day.label("order_day"),
                func.count(func.distinct(Order.id_order)).label("orders"),
                func.sum(OrderDetail.subtotal).label("sales"),
            )
            .join(OrderDetail, OrderDetail.id_order == Order.id_order)
            .where(
                Order.delivery_date >= start.date(),
                Order.delivery_date < end.date(),
                Order.state.in_(BILLABLE_STATES),
            )
            .group_by("order_day")
        )
        exported = (
            select(
                ShiftClosure.closure_date,
                func.sum(ShiftClosure.total_orders),
                func.sum(ShiftClosure.total_sales),
            )
            .where(
                ShiftClosure.closure_date >= start.date(),
                ShiftClosure.closure_date < end.date(),
                ShiftClosure.exported_siigo.is_(True),
            )
            .group_by(ShiftClosure.closure_date)
        )
        closed = {day: (orders, sales) for day, orders, sales in db.execute(exported)}
        return sorted(
            row.order_day
            for row in db.execute(billable)
            if closed.get(row.order_day) != (row.orders, row.sales)
        )


# Intancia del repositorio inyectando el modelo ORM
shift_closure_repository = RepositoryShiftClosure(ShiftClosure)
