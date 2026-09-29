from app.models.securityModule.role import Role
from app.repositories.base_repository import BaseRepository
from app.schemas.securityModule.role_schema import RoleCreate, RoleUpdate


class RepositoryRole(BaseRepository[Role, RoleCreate, RoleUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
role_repository = RepositoryRole(Role)
