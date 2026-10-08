from datetime import datetime

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class SessionCreate(BaseModel):
    id_user: int
    refresh_token_hash: str
    expires_at: datetime
    user_agent: str | None = None
    ip_address: str | None = None


class SessionUpdate(BaseModel):
    revoked: bool | None = None
