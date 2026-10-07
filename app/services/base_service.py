from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.strategies.deletion_strategy import (
    DeletionStrategy,
    HardDeleteStrategy,
    SoftDeleteStrategy,
)
from app.db.database import Base
from app.services.validation import (
    ReferenceRule,
    UniqueRule,
    UniqueTogether,
    ensure_reference,
    ensure_unique,
)
from app.utils.enums.delete_type import DeletionType
from app.utils.exceptions.business_exceptions import (
    EntityNotFoundError,
)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

# Reglas de Validacion
__all__ = ["BaseService", "ReferenceRule", "UniqueRule", "UniqueTogether"]


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    # Reglas declarativas: cada servicio sobrescribe las que necesite
    unique_rules: tuple[UniqueRule, ...] = ()
    references: tuple[ReferenceRule, ...] = ()
    unique_together: tuple[UniqueTogether, ...] = ()

    def __init__(self, repository: Any, entity_name: str = "Entidad"):
        self.repository = repository
        self.entity_name = entity_name

    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        return self.repository.get_all(db, skip=skip, limit=limit)

    def get(self, db: Session, id: Any) -> ModelType:
        obj = self.repository.get(db, id=id)
        if obj is None:
            raise EntityNotFoundError(self.entity_name, id)
        return obj

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        self._validate_before_create(db, obj_in)
        obj_in = self._before_create(obj_in)
        return self.repository.create(db, obj_in=obj_in)

    def update(self, db: Session, *, id: Any, obj_in: UpdateSchemaType) -> ModelType:
        db_obj = self.get(db, id)
        self._validate_before_update(db, obj_in, db_obj)
        return self.repository.update(db, db_obj=db_obj, obj_in=obj_in)

    def remove(
        self, db: Session, *, id: Any, strategy_type: DeletionType = DeletionType.SOFT
    ) -> ModelType:

        strategies: dict[DeletionType, DeletionStrategy] = {
            DeletionType.SOFT: SoftDeleteStrategy(),
            DeletionType.HARD: HardDeleteStrategy(),
        }

        strategy = strategies.get(strategy_type)

        # Inyectarel contexto actual (db, repositorio inyectado y el id) a la estrategia
        return strategy.execute(db, self.repository, id)  # type: ignore

    # --- Hooks opcionales (se sobrescriben en el servicio específico) ---

    def _validate_before_create(self, db: Session, obj_in: CreateSchemaType) -> None:
        for rule in self._declared_rules():
            rule.on_create(db, self.repository, obj_in)

    def _validate_before_update(
        self, db: Session, obj_in: UpdateSchemaType, existing: ModelType
    ) -> None:
        for rule in self._declared_rules():
            rule.on_update(db, self.repository, obj_in, existing)

    def _before_create(self, obj_in: CreateSchemaType) -> CreateSchemaType:
        """Transforma los datos justo antes de persistir (p. ej. hashear)."""
        return obj_in

    # --- Utilidades para los servicios con validaciones propias ---

    def _declared_rules(self) -> tuple[Any, ...]:
        return (*self.unique_rules, *self.references, *self.unique_together)

    def _ensure_unique(
        self, db: Session, field: str, value: Any, *, label: str, **options: Any
    ) -> None:
        ensure_unique(db, self.repository, field, value, label=label, **options)

    def _ensure_reference(
        self, db: Session, repository: Any, id: Any, *, field: str, label: str
    ) -> None:
        ensure_reference(db, repository, id, field=field, label=label)
