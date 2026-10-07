from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import Base
from app.utils.exceptions.business_exceptions import (
    ConflictError,
    EntityNotFoundError,
)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
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

    def remove(self, db: Session, *, id: Any) -> ModelType:
        self.get(db, id)
        return self.repository.remove(db, id=id)

    # --- Hooks opcionales (se sobrescriben en el servicio específico) ---

    def _validate_before_create(self, db: Session, obj_in: CreateSchemaType) -> None:
        """Validaciones de negocio antes de crear. Lanza BusinessError si fallan."""

    def _validate_before_update(
        self, db: Session, obj_in: UpdateSchemaType, existing: ModelType
    ) -> None:
        """Validaciones de negocio antes de actualizar."""

    def _before_create(self, obj_in: CreateSchemaType) -> CreateSchemaType:
        """Transforma los datos justo antes de persistir (p. ej. hashear)."""
        return obj_in

    # --- Utilidad para los hooks ---

    def _ensure_unique(
        self,
        db: Session,
        field: str,
        value: Any,
        *,
        label: str,
        exclude: ModelType | None = None,
    ) -> None:
        if self.repository.exists(db, exclude=exclude, **{field: value}):
            raise ConflictError(f"{label} ya registrado: '{value}'.", field=field)
