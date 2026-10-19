from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    # Cookie httpOnly del refresh token. En producción: COOKIE_SECURE=true (HTTPS).
    # SameSite "lax" sirve si front y API comparten dominio (o el proxy de dev);
    # con dominios distintos se necesita "none" (que exige Secure).
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    COOKIE_DOMAIN: str | None = None
    CORS_ORIGINS: list[str] = []
    GOOGLE_CREDENTIALS_FILE: Path | None = None
    # Meses que se conservan en la BD (incluido el vigente). Con 2: en octubre
    # se conservan octubre y septiembre; agosto y anteriores se pueden purgar.
    HISTORY_RETENTION_MONTHS: int = Field(2, ge=1)
    # Código (user_vehicle.code) del vendedor al que el cierre asigna los
    # pedidos despachados/entregados sin conductor. Siigo lo recibe como 1.
    DEFAULT_SELLER_CODE: str = Field("01", min_length=2, max_length=2)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Instancia de las las configuraciones para usarlas en toda la app
settings = Settings()  # type: ignore
