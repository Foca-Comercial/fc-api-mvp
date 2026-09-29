from app.models.securityModule.user_role import UserRole
from app.repositories.base_repository import BaseRepository
from app.schemas.securityModule.user_role_schema import UserRoleCreate, UserRoleUpdate


class RepositoryUser(BaseRepository[UserRole, UserRoleCreate, UserRoleUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
user_role_repository = RepositoryUser(UserRole)
