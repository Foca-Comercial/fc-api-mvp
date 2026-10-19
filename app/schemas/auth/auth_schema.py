from datetime import datetime

from pydantic import BaseModel


class Token(BaseModel):
    """Lo que ve el cliente en el body: el refresh token viaja en cookie httpOnly."""

    access_token: str
    token_type: str = "bearer"


class TokenPair(Token):
    """Uso interno del service: el router saca el refresh token hacia la cookie."""

    refresh_token: str


class SessionCreate(BaseModel):
    id_user: int
    refresh_token_hash: str
    expires_at: datetime
    user_agent: str | None = None
    ip_address: str | None = None


class SessionUpdate(BaseModel):
    revoked: bool | None = None
