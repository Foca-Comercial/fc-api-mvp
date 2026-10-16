from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    GOOGLE_CREDENTIALS_FILE: Path | None = None
    # Meses que se conservan en la BD (incluido el vigente). Con 2: en octubre
    # se conservan octubre y septiembre; agosto y anteriores se pueden purgar.
    HISTORY_RETENTION_MONTHS: int = Field(2, ge=1)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Instancia de las las configuraciones para usarlas en toda la app
settings = Settings()  # type: ignore
