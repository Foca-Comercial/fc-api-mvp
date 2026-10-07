from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.utils.exceptions.business_exceptions import (
    BusinessValidationError,
    ConflictError,
)

# --- Comprobaciones reutilizables (las usan las reglas y los servicios) ---


def ensure_unique(
    db: Session,
    repository: Any,
    field: str,
    value: Any,
    *,
    label: str,
    exclude: Any = None,
    normalized: bool = False,
    **scope: Any,  # acota la unicidad (p. ej. id_zone=3)
) -> None:
    if normalized:
        found = repository.exists_normalized(db, field, value, exclude=exclude, **scope)
    else:
        found = repository.exists(db, exclude=exclude, **{field: value, **scope})
    if found:
        raise ConflictError(f"{label} ya registrado: '{value}'", field=field)


def ensure_reference(
    db: Session, repository: Any, id: Any, *, field: str, label: str
) -> None:
    """Verifica que la entidad referenciada exista y esté activa."""
    obj = repository.get(db, id)
    if obj is None:
        raise BusinessValidationError(f"{label} con ID {id} no existe.", field=field)
    if not getattr(obj, "active", True):
        raise BusinessValidationError(
            f"{label} con ID {id} está inactivo.",
            field=field,
            code="REFERENCE_INACTIVE",
        )


def ensure_unique_together(
    db: Session,
    repository: Any,
    label: str,
    values: dict[str, Any],
    *,
    exclude: Any = None,
) -> None:
    if repository.exists(db, exclude=exclude, **values):
        raise ConflictError(
            f"La combinación {label} ya está registrada.",
            code="DUPLICATE_PAIR",
            field=next(iter(values)),
        )


# --- Reglas declarativas ---
# Cada regla recibe el repositorio del servicio que la declara.


@dataclass(frozen=True)
class UniqueRule:
    field: str
    label: str
    normalized: bool = True  # compara ignorando mayúsculas y espacios

    def on_create(self, db: Session, repository: Any, obj_in: BaseModel) -> None:
        ensure_unique(
            db,
            repository,
            self.field,
            getattr(obj_in, self.field),
            label=self.label,
            normalized=self.normalized,
        )

    def on_update(
        self, db: Session, repository: Any, obj_in: BaseModel, existing: Any
    ) -> None:
        value = getattr(obj_in, self.field, None)
        if value is not None:  # solo lo que el cliente envió
            ensure_unique(
                db,
                repository,
                self.field,
                value,
                label=self.label,
                normalized=self.normalized,
                exclude=existing,
            )


@dataclass(frozen=True)
class ReferenceRule:
    field: str  # campo FK en el schema, p. ej. "id_user"
    label: str  # nombre legible, p. ej. "Usuario"
    repository: Any  # INSTANCIA del repositorio de la entidad referenciada

    def on_create(self, db: Session, repository: Any, obj_in: BaseModel) -> None:
        ensure_reference(
            db,
            self.repository,
            getattr(obj_in, self.field),
            field=self.field,
            label=self.label,
        )

    def on_update(
        self, db: Session, repository: Any, obj_in: BaseModel, existing: Any
    ) -> None:
        # Solo se revalida si cambió: un registro cuyo padre se desactivó
        # después debe poder seguir editándose.
        value = getattr(obj_in, self.field, None)
        if value is not None and value != getattr(existing, self.field):
            ensure_reference(
                db, self.repository, value, field=self.field, label=self.label
            )


@dataclass(frozen=True)
class UniqueTogether:
    label: str  # p. ej. "Usuario y rol"
    fields: tuple[str, ...]  # p. ej. ("id_user", "id_role")

    def on_create(self, db: Session, repository: Any, obj_in: BaseModel) -> None:
        values = {f: getattr(obj_in, f) for f in self.fields}
        ensure_unique_together(db, repository, self.label, values)

    def on_update(
        self, db: Session, repository: Any, obj_in: BaseModel, existing: Any
    ) -> None:
        sent = {f: getattr(obj_in, f, None) for f in self.fields}
        if all(v is None for v in sent.values()):
            return
        # La pareja se evalúa con los valores finales: lo enviado más lo que
        # el registro ya tenía.
        values = {
            f: v if v is not None else getattr(existing, f) for f, v in sent.items()
        }
        ensure_unique_together(db, repository, self.label, values, exclude=existing)
