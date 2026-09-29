from app.models.coreModule.shift_closure import ShiftClosure
from app.repositories.base_repository import BaseRepository
from app.schemas.coreModule.shift_closure_schema import (
    ShiftClosureCreate,
    ShiftClosureUpdate,
)


class RepositoryShiftClosure(
    BaseRepository[ShiftClosure, ShiftClosureCreate, ShiftClosureUpdate]
):
    pass


# Intancia del repositorio inyectando el modelo ORM
shift_closure_repository = RepositoryShiftClosure(ShiftClosure)
