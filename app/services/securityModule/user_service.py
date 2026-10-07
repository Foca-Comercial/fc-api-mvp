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

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        secured_obj = obj_in.model_copy(
            update={"password": hash_password(obj_in.password)}
        )
        return super().create(db, obj_in=secured_obj)


# Instancia única para inyectar en el router
user_service = UserService()
