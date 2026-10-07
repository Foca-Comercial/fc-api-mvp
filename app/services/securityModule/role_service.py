from app.models.securityModule.role import Role
from app.repositories.securityModule.role_repository import role_repository
from app.schemas.securityModule.role_schema import RoleCreate, RoleUpdate
from app.services.base_service import BaseService, UniqueRule


class RoleService(BaseService[Role, RoleCreate, RoleUpdate]):
    unique_rules = (UniqueRule("name", "Nombre de rol"),)

    def __init__(self):
        # Inyectar el repositorio instanciado y el nombre para el error 404
        super().__init__(repository=role_repository, entity_name="Rol")


# Instancia única para inyectar en el router
role_service = RoleService()
