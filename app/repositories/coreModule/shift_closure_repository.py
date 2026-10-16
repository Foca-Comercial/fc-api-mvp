from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.coreModule.shift_closure import ShiftClosure
from app.repositories.base_repository import BaseRepository
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


# Intancia del repositorio inyectando el modelo ORM
shift_closure_repository = RepositoryShiftClosure(ShiftClosure)
