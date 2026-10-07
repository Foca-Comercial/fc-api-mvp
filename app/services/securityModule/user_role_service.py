from app.models.securityModule.user_role import UserRole
from app.repositories.securityModule.role_repository import (
    role_repository,
)
from app.repositories.securityModule.user_repository import (
    user_repository,
)
from app.repositories.securityModule.user_role_repository import user_role_repository
from app.schemas.securityModule.user_role_schema import UserRoleCreate, UserRoleUpdate
from app.services.base_service import BaseService
from app.services.validation import ReferenceRule, UniqueTogether


class UserRoleService(BaseService[UserRole, UserRoleCreate, UserRoleUpdate]):
    references = (
        ReferenceRule("id_user", "Usuario", user_repository),
        ReferenceRule("id_role", "Rol", role_repository),
    )
    unique_together = (UniqueTogether("Usuario y rol", ("id_user", "id_role")),)

    def __init__(self):
        # Inyectamos el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=user_role_repository, entity_name="UsuarioRol")


# Instancia única para inyectar en el router
user_role_service = UserRoleService()
