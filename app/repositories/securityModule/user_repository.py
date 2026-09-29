from app.models.securityModule.user import User
from app.repositories.base_repository import BaseRepository
from app.schemas.securityModule.user_schema import UserCreate, UserUpdate


class RepositoryUser(BaseRepository[User, UserCreate, UserUpdate]):
    pass


# Intancia del repositorio inyectando el modelo ORM
user_repository = RepositoryUser(User)
