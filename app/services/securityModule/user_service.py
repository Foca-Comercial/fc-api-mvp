from sqlalchemy.orm import Session

from app.models.securityModule.user import User
from app.repositories.securityModule.person_repository import (
    person_repository,  # instancia
)
from app.repositories.securityModule.user_repository import user_repository
from app.schemas.securityModule.user_schema import UserCreate, UserUpdate
from app.services.base_service import BaseService, UniqueRule
from app.utils.exceptions.business_exceptions import ConflictError
from app.utils.helpers.password_helper import hash_password


class UserService(BaseService[User, UserCreate, UserUpdate]):
    unique_rules = (UniqueRule("username", "Nombre de usuario", normalized=False),)

    def __init__(self):
        # Inyectar el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=user_repository, entity_name="Usuario")

    def _validate_before_create(self, db: Session, obj_in: UserCreate) -> None:
        super()._validate_before_create(db, obj_in)  # unicidad del username
        self._ensure_person_available(db, obj_in.id_person)

    def _validate_before_update(
        self, db: Session, obj_in: UserUpdate, existing: User
    ) -> None:
        super()._validate_before_update(db, obj_in, existing)
        if obj_in.id_person is not None and obj_in.id_person != existing.id_person:
            self._ensure_person_available(db, obj_in.id_person)

    def _before_create(self, obj_in: UserCreate) -> UserCreate:
        return obj_in.model_copy(update={"password": hash_password(obj_in.password)})

    def _ensure_person_available(self, db: Session, id_person: int) -> None:
        self._ensure_reference(
            db, person_repository, id_person, field="id_person", label="Persona"
        )
        if user_repository.exists(db, id_person=id_person):
            raise ConflictError(
                f"La persona con ID {id_person} ya tiene un usuario asignado.",
                field="id_person",
            )


# Instancia única para inyectar en el router
user_service = UserService()
