from typing import Any, Generic, Type, TypeVar  # noqa: F401, UP035

from pydantic import BaseModel
from sqlalchemy import exists as sa_exists
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import Base

# Definimos los genéricos:
# ModelType = Entidad ORM (SQLAlchemy)
# CreateSchemaType / UpdateSchemaType = DTOs de Pydantic
ModelType = TypeVar("ModelType", bound=Base)  # type: ignore
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model
        mapper = sa_inspect(model)
        self._primary_key_columns = list(mapper.primary_key)

    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        # db.scalars() extrae directamente los objetos de la respuesta
        stmt = select(self.model).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    def get(self, db: Session, id: Any) -> ModelType | None:
        # db.get() es la sintaxis optimizada de SQLAlchemy 2.0 para buscar por PK
        return db.get(self.model, id)

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        # Convertir el DTO de Pydantic a un diccionario y lo se pasa al modelo ORM
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        # Extraer los datos actuales del objeto en BD
        obj_data = db_obj.__dict__

        # Si llega como DTO, excluir los campos no enviados (Oh, estas haciendo magia para PATCH. Continua)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # Actualizar solo los campos que vinieron en el request
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> ModelType | None:
        obj = db.get(self.model, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def exists(
        self, db: Session, *, exclude: ModelType | None = None, **filters: Any
    ) -> bool:
        """Indica si hay algún registro que cumpla los filtros.

        `exclude` omite un registro concreto (útil al validar en una actualización).
        """
        conditions = [
            getattr(self.model, field) == value for field, value in filters.items()
        ]
        if exclude is not None:
            pk_column = self._primary_key_columns[0]  # type: ignore
            conditions.append(pk_column != sa_inspect(exclude).identity[0])  # type: ignore
        return bool(db.scalar(select(sa_exists().where(*conditions))))
