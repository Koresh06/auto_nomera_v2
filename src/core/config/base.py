from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "APP_NAME"
    debug: bool = True
    use_fake_stars: bool = True
    hold_slots_time: int = 300
    pre_publication_window_hours: int = 2
