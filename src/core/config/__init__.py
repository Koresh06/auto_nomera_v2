from pydantic_settings import BaseSettings, SettingsConfigDict
from src.core.config.base import Settings
from src.core.config.database import DatabaseSettings


class AppSettings(BaseSettings):
    app: Settings = Settings()
    db: DatabaseSettings = DatabaseSettings()

    model_config = SettingsConfigDict(
        env_file=(".env"),
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
    )


settings = AppSettings()