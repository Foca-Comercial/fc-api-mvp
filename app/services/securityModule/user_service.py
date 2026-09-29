from app.models.securityModule.user import User
from app.repositories.securityModule.user_repository import user_repository
from app.schemas.securityModule.user_schema import UserCreate, UserUpdate
from app.services.base_service import BaseService


class UserService(BaseService[User, UserCreate, UserUpdate]):
    def __init__(self):
        # Inyectar el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=user_repository, entity_name="Usuario")


# Instancia única para inyectar en el router
user_service = UserService()
