from pydantic_settings import BaseSettings


class PostgresSettings(BaseSettings):
    name: str = "name"
    password: str = "12345"
    user: str = "user"
    host: str = "0.0.0.0"
    port: int = 5432
    echo: bool = False
    pool_size: int = 50
    max_overflow: int = 10

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    

class RedisSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: str = "6379"
    db: int = 0

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"
    

class DatabaseSettings(BaseSettings):
    postgres: PostgresSettings = PostgresSettings()
    redis: RedisSettings = RedisSettings()