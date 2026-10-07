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
    def execute(self, db: Session, repository: BaseRepository, entity_id: Any) -> Any:
        pass


class SoftDeleteStrategy(DeletionStrategy):
    """Eliminación parcial: Cambia el estado 'active' a False."""

    def execute(self, db: Session, repository: BaseRepository, entity_id: Any) -> Any:
        obj = repository.get(db, entity_id)
        if not obj:
            raise EntityNotFoundError(repository.model.__name__, entity_id)

        # Validar que la entidad realmente soporte eliminación lógica
        if not hasattr(obj, "active"):
            raise BusinessRuleViolationError(
                f"La entidad {repository.model.__name__} no soporta eliminación parcial porque no tiene el atributo 'active'."
            )

        # Reutilizar el método update del repositorio base pasando un diccionario
        return repository.update(db, db_obj=obj, obj_in={"active": False})


class HardDeleteStrategy(DeletionStrategy):
    """Eliminación directa: Borra el registro físicamente de la base de datos."""

    def execute(self, db: Session, repository: BaseRepository, entity_id: Any) -> Any:
        obj = repository.remove(db, id=entity_id)
        if not obj:
            raise EntityNotFoundError(repository.model.__name__, entity_id)
        return obj
