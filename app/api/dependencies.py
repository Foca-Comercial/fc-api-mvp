from dataclasses import dataclass

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.securityModule.user import User
from app.repositories.securityModule.user_repository import user_repository
from app.schemas.common.page_schema import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageParams
from app.utils.exceptions.business_exceptions import ForbiddenError, UnauthorizedError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

ADMIN_ROLE = "ADMINISTRADOR"


@dataclass
class CurrentUser:
    user: User
    roles: list[str]


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),  # noqa: B008
) -> CurrentUser:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Token inválido.")

    user = user_repository.get(db, int(user_id))
    if user is None or not user.active:
        raise UnauthorizedError("El usuario del token ya no existe o está inactivo.")

    roles = payload.get("roles", [])
    return CurrentUser(user=user, roles=roles)


def require_roles(*allowed_roles: str):
    """
    Dependencia de segundo nivel: exige que el usuario tenga alguno de los
    roles indicados. ADMINISTRADOR siempre pasa, sin importar los roles pedidos.
    """

    def dependency(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:  # noqa: B008
        if ADMIN_ROLE in current.roles:
            return current

        if not any(role in current.roles for role in allowed_roles):
            effective_roles = sorted({ADMIN_ROLE, *allowed_roles})
            raise ForbiddenError(
                f"Se requiere alguno de estos roles: {', '.join(effective_roles)}."
            )
        return current

    return dependency


def get_page_params(
    page: int = Query(1, ge=1, description="Página (1 = la primera)"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Registros por página"
    ),
) -> PageParams:
    """Página pedida en los listados paginados en el servidor:

    def list_x(params: PageParams = Depends(get_page_params), ...): ...
    """
    return PageParams(page=page, page_size=page_size)
