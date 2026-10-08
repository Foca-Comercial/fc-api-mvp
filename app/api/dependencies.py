from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.securityModule.user import User
from app.repositories.securityModule.user_repository import user_repository
from app.utils.exceptions.business_exceptions import UnauthorizedError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Token inválido.")

    user = user_repository.get(db, int(user_id))
    if user is None or not user.active:
        raise UnauthorizedError("El usuario del token ya no existe o está inactivo.")
    return user
