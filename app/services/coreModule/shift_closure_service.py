from app.models.coreModule.shift_closure import ShiftClosure
from app.repositories.coreModule.shift_closure_repository import (
    shift_closure_repository,
)
from app.schemas.coreModule.shift_closure_schema import (
    ShiftClosureCreate,
    ShiftClosureUpdate,
)
from app.services.base_service import BaseService


class ShiftClosureService(
    BaseService[ShiftClosure, ShiftClosureCreate, ShiftClosureUpdate]
):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=shift_closure_repository, entity_name="CierreTurno")


# Instancia única para inyectar en el closurer
shift_closure_service = ShiftClosureService()
