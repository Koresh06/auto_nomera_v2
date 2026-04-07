from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    name: str = "name"
    password: str = "12345"
    user: str = "user"
    host: str = "0.0.0.0"
    port: int = 5432
    echo: bool = False
    pool_size: int = 50
    max_overflow: int = 10

    redis_host: str = "0.0.0.0"
    redis_port: str = "6379"

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"
