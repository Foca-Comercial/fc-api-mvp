from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.base_repository import BaseRepository
from app.utils.exceptions.business_exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)


class DeletionStrategy(ABC):
    """Interfaz base para las estrategias de eliminación."""

    @abstractmethod
    def execute(
        self, db: Session, repository: BaseRepository, entity_id: Any, entity_name: str
    ) -> Any:
        pass


class SoftDeleteStrategy(DeletionStrategy):
    """Eliminación parcial: Cambia el estado 'active' a False."""

    def execute(self, db, repository, entity_id, entity_name):
        obj = repository.get(db, entity_id)
        if not obj:
            raise EntityNotFoundError(entity_name, entity_id)
        if not hasattr(obj, "active"):
            raise BusinessRuleViolationError(
                f"La entidad {entity_name} no soporta eliminación parcial (sin atributo 'active')."
            )
        return repository.update(db, db_obj=obj, obj_in={"active": False})


class HardDeleteStrategy(DeletionStrategy):
    """Eliminación directa: Borra el registro físicamente de la base de datos."""

    def execute(self, db, repository, entity_id, entity_name):
        obj = repository.remove(db, id=entity_id)
        if not obj:
            raise EntityNotFoundError(entity_name, entity_id)
        return obj
