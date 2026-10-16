import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings
from app.utils.exceptions.business_exceptions import UnauthorizedError


def create_access_token(subject: str | int, *, roles: list[str] | None = None) -> str:
    """Genera un JWT firmado, con el id del usuario como `sub` y expiración."""
    expire = datetime.now(timezone.utc) + timedelta(  # noqa: UP017
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire}
    if roles is not None:
        payload["roles"] = roles
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida el JWT. Traduce fallos de la librería a errores de negocio."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError as exc:
        raise UnauthorizedError("La sesión expiró, inicia sesión nuevamente.") from exc
    except InvalidTokenError as exc:
        raise UnauthorizedError("Token inválido.") from exc


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
