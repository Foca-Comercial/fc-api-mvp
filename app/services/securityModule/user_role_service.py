from app.models.securityModule.user_role import UserRole
from app.repositories.securityModule.user_role_repository import user_role_repository
from app.schemas.securityModule.user_role_schema import UserRoleCreate, UserRoleUpdate
from app.services.base_service import BaseService


class UserRoleService(BaseService[UserRole, UserRoleCreate, UserRoleUpdate]):
    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=user_role_repository, entity_name="UsuarioRol")


# Instancia única para inyectar en el router
user_role_service = UserRoleService()
