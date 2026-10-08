from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.securityModule.user_session import UserSession
from app.repositories.base_repository import BaseRepository
from app.schemas.auth.auth_schema import SessionCreate, SessionUpdate


class RepositoryUserSession(BaseRepository[UserSession, SessionCreate, SessionUpdate]):
    def get_by_token_hash(self, db: Session, token_hash: str) -> UserSession | None:
        """Solo sesiones activas (no revocadas) — uso normal del refresh."""
        stmt = select(UserSession).where(
            UserSession.refresh_token_hash == token_hash,
            UserSession.revoked.is_(False),
        )
        return db.scalars(stmt).first()

    def get_by_token_hash_any(self, db: Session, token_hash: str) -> UserSession | None:
        """Ignora el estado revocado — se usa solo para detectar reutilización."""
        stmt = select(UserSession).where(UserSession.refresh_token_hash == token_hash)
        return db.scalars(stmt).first()

    def revoke(self, db: Session, session: UserSession) -> None:
        session.revoked = True
        db.add(session)
        db.commit()

    def revoke_all_for_user(self, db: Session, id_user: int) -> None:
        stmt = select(UserSession).where(
            UserSession.id_user == id_user, UserSession.revoked.is_(False)
        )
        for session in db.scalars(stmt).all():
            session.revoked = True
        db.commit()


user_session_repository = RepositoryUserSession(UserSession)
