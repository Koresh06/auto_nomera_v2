from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "APP_NAME"
    debug: bool = False
    sentry_dsn: str | None = None
    use_fake_stars: bool = False
    hold_slots_time: int = 300
    pre_publication_window_hours: int = 2
