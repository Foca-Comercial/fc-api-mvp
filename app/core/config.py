from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    GOOGLE_CREDENTIALS_FILE: Path

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Instancia de las las configuraciones para usarlas en toda la app
settings = Settings()  # type: ignore
