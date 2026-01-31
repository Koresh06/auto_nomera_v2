from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "APP_NAME"
    debug: bool = True
    use_fake_stars: bool = True