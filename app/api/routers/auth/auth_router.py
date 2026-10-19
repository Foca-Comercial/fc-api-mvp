from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.schemas.auth.auth_schema import Token
from app.services.auth.auth_service import auth_service
from app.utils.exceptions.business_exceptions import UnauthorizedError

router = APIRouter(prefix="/auth", tags=["Auth"])

# El refresh token viaja en una cookie httpOnly (JavaScript no puede leerla) y solo
# se envía a /api/v1/auth/*, no a cada petición de la API.
REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    # Debe usar los mismos path/domain que al crearla, si no el navegador no la borra
    response.delete_cookie(
        key=REFRESH_COOKIE,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )


@router.post("/login", response_model=Token)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    tokens = auth_service.login(
        db,
        username=form_data.username,
        password=form_data.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens  # response_model=Token deja fuera el refresh_token del body


@router.post("/refresh", response_model=Token)
def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),  # noqa: B008
):
    if not refresh_token:
        raise UnauthorizedError("No hay una sesión activa, inicia sesión.")
    tokens = auth_service.refresh(
        db,
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),  # noqa: B008
):
    if refresh_token:
        auth_service.logout(db, refresh_token=refresh_token)
    _clear_refresh_cookie(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(
    response: Response,
    db: Session = Depends(get_db),  # noqa: B008
    current: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Cierra todas las sesiones del usuario autenticado (ej. 'cerrar sesión en todos los dispositivos')."""
    auth_service.logout_all(db, id_user=current.user.id_user)
    _clear_refresh_cookie(response)
