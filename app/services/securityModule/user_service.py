from sqlalchemy.orm import Session

from app.models.securityModule.user import User
from app.repositories.securityModule.user_repository import user_repository
from app.schemas.securityModule.user_schema import UserCreate, UserUpdate
from app.services.base_service import BaseService
from app.utils.helpers.password_helper import hash_password


class UserService(BaseService[User, UserCreate, UserUpdate]):
    def __init__(self):
        # Inyectar el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=user_repository, entity_name="Usuario")

    def _validate_before_create(self, db: Session, obj_in: UserCreate) -> None:
        self._ensure_unique(db, "username", obj_in.username, label="Nombre de usuario")

    def _validate_before_update(
        self, db: Session, obj_in: UserUpdate, existing: User
    ) -> None:
        # Solo si el cliente envió un username distinto al actual
        if obj_in.username is not None and obj_in.username != existing.username:
            self._ensure_unique(
                db,
                "username",
                obj_in.username,
                label="Nombre de usuario",
                exclude=existing,
            )

    def _before_create(self, obj_in: UserCreate) -> UserCreate:
        return obj_in.model_copy(update={"password": hash_password(obj_in.password)})


# Instancia única para inyectar en el router
user_service = UserService()
