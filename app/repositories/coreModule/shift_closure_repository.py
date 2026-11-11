from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.timezone import bogota_month_range
from app.models.coreModule.shift_closure import ShiftClosure
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.shift_closure_schema import (
    ShiftClosureCreate,
    ShiftClosureUpdate,
)


@dataclass(frozen=True)
class ExportedClosure:
    """Lo que se guarda de un vendedor al exportar el cierre del día."""

    id_user_vehicle: int
    total_orders: int
    total_sales: Decimal
    signature: str


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
    def save_exported(
        self, db: Session, day: date, closures: Sequence[ExportedClosure]
    ) -> None:
        ids = [c.id_user_vehicle for c in closures]
        db.execute(
            delete(ShiftClosure).where(
                ShiftClosure.closure_date == day,
                ShiftClosure.id_user_vehicle.not_in(ids),
            )
        )
        if not closures:
            return
        stmt = insert(ShiftClosure).values(
            [
                {
                    "closure_date": day,
                    "id_user_vehicle": c.id_user_vehicle,
                    "total_orders": c.total_orders,
                    "total_sales": c.total_sales,
                    "signature": c.signature,
                    "exported_siigo": True,
                    "exported_at": func.now(),
                }
                for c in closures
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_shift_closure_date_vehicle",
            set_={
                "total_orders": stmt.excluded.total_orders,
                "total_sales": stmt.excluded.total_sales,
                "signature": stmt.excluded.signature,
                "exported_siigo": True,
                "exported_at": stmt.excluded.exported_at,
            },
        )
        db.execute(stmt)

    # Cierres exportados del mes: {día: {id_user_vehicle: ShiftClosure}}. La purga
    # los compara con los pedidos actuales (ShiftClosureService.unclosed_days).
    def get_exported_in_month(
        self, db: Session, month: date
    ) -> dict[date, dict[int, ShiftClosure]]:
        start, end = bogota_month_range(month.year, month.month)
        stmt = select(ShiftClosure).where(
            ShiftClosure.closure_date >= start.date(),
            ShiftClosure.closure_date < end.date(),
            ShiftClosure.exported_siigo.is_(True),
        )
        by_day: dict[date, dict[int, ShiftClosure]] = {}
        for closure in db.scalars(stmt).all():
            by_day.setdefault(closure.closure_date, {})[closure.id_user_vehicle] = (
                closure
            )
        return by_day


# Intancia del repositorio inyectando el modelo ORM
shift_closure_repository = RepositoryShiftClosure(ShiftClosure)
