from typing import Any, Generic, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import Base

ModelType = TypeVar("ModelType", bound=Base)  # type: ignore
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
        # Centralizamos la regla de negocio del 404
        obj = self.repository.get(db, id=id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.entity_name} con ID {id} no encontrada.",
            )
        return obj

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        return self.repository.create(db, obj_in=obj_in)

    def update(self, db: Session, *, id: Any, obj_in: UpdateSchemaType) -> ModelType:
        # Reutilizamos el get() para validar que exista antes de actualizar
        db_obj = self.get(db, id)
        return self.repository.update(db, db_obj=db_obj, obj_in=obj_in)

    def remove(self, db: Session, *, id: Any) -> ModelType:
        # Reutilizamos el get() para validar que exista antes de eliminar
        self.get(db, id)
        return self.repository.remove(db, id=id)
