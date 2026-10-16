from datetime import date

from sqlalchemy import select
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
    # Cierres guardados de un día: {id_user_vehicle: ShiftClosure}
    def get_by_date(self, db: Session, day: date) -> dict[int, ShiftClosure]:
        stmt = select(ShiftClosure).where(ShiftClosure.closure_date == day)
        return {c.id_user_vehicle: c for c in db.scalars(stmt).all()}


# Intancia del repositorio inyectando el modelo ORM
shift_closure_repository = RepositoryShiftClosure(ShiftClosure)
