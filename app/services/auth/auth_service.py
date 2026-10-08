from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.securityModule.user import User
from app.repositories.securityModule.user_repository import user_repository
from app.utils.exceptions.business_exceptions import UnauthorizedError
from app.utils.helpers.password_helper import verify_password


class AuthService:
    def authenticate(self, db: Session, *, username: str, password: str) -> User:
        user = user_repository.get_by_username_with_roles(db, username)
        if user is None or not verify_password(password, user.password):
            raise UnauthorizedError("Usuario o contraseña incorrectos.")
        if not user.active:
            raise UnauthorizedError("El usuario está inactivo.")
        return user

    def login(self, db: Session, *, username: str, password: str) -> str:
        user = self.authenticate(db, username=username, password=password)
        role_names = [ur.role.name for ur in user.user_roles]
        return create_access_token(subject=user.id_user, roles=role_names)


auth_service = AuthService()
