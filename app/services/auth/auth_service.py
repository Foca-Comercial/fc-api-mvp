from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.models.securityModule.user import User
from app.repositories.securityModule.user_repository import user_repository
from app.repositories.securityModule.user_session_repository import (
    user_session_repository,
)
from app.schemas.auth.auth_schema import SessionCreate, Token
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

    def login(
        self,
        db: Session,
        *,
        username: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> Token:
        user = self.authenticate(db, username=username, password=password)
        return self._issue_tokens(
            db, user, user_agent=user_agent, ip_address=ip_address
        )

    def refresh(
        self,
        db: Session,
        *,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> Token:
        token_hash = hash_refresh_token(refresh_token)
        # Bloquea la sesión: dos refresh simultáneos con el mismo token no pueden
        # rotarla dos veces. El segundo espera y luego cae en "reutilización".
        session = user_session_repository.get_by_token_hash(
            db, token_hash, for_update=True
        )

        if session is None:
            # No existe como sesión activa: nunca existió, o ya fue usada antes
            # (rotación). Si el hash existe pero revocado, es reutilización:
            # señal de robo -> se cierran TODAS las sesiones del usuario.
            stale = user_session_repository.get_by_token_hash_any(db, token_hash)
            if stale is not None:
                user_session_repository.revoke_all_for_user(db, stale.id_user)
            raise UnauthorizedError("Sesión inválida, inicia sesión nuevamente.")

        if session.expires_at < datetime.now(timezone.utc):
            user_session_repository.revoke(db, session)
            raise UnauthorizedError("La sesión expiró, inicia sesión nuevamente.")

        user = user_repository.get_by_id_with_roles(db, session.id_user)
        if user is None or not user.active:
            raise UnauthorizedError("El usuario ya no existe o está inactivo.")

        # Rotación atómica: la revocación se confirma en el mismo commit que crea
        # la sesión nueva (en _issue_tokens), y el bloqueo dura hasta entonces.
        user_session_repository.revoke(db, session, commit=False)
        return self._issue_tokens(
            db, user, user_agent=user_agent, ip_address=ip_address
        )

    def logout(self, db: Session, *, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        session = user_session_repository.get_by_token_hash(db, token_hash)
        if session is not None:
            user_session_repository.revoke(db, session)

    def logout_all(self, db: Session, *, id_user: int) -> None:
        user_session_repository.revoke_all_for_user(db, id_user)

    def _issue_tokens(
        self,
        db: Session,
        user: User,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> Token:
        role_names = [ur.role.name for ur in user.user_roles]
        access_token = create_access_token(subject=user.id_user, roles=role_names)

        refresh_token = generate_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        user_session_repository.create(
            db,
            obj_in=SessionCreate(
                id_user=user.id_user,
                refresh_token_hash=hash_refresh_token(refresh_token),
                expires_at=expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            ),
        )
        return Token(access_token=access_token, refresh_token=refresh_token)


auth_service = AuthService()
