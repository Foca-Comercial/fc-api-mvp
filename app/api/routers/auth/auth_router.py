from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.db.database import get_db
from app.schemas.auth.auth_schema import RefreshRequest, Token
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    return auth_service.login(
        db,
        username=form_data.username,
        password=form_data.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: Request,
    body: RefreshRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    return auth_service.refresh(
        db,
        refresh_token=body.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):  # noqa: B008
    auth_service.logout(db, refresh_token=body.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(
    db: Session = Depends(get_db),  # noqa: B008
    current: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Cierra todas las sesiones del usuario autenticado (ej. 'cerrar sesión en todos los dispositivos')."""
    auth_service.logout_all(db, id_user=current.user.id_user)
