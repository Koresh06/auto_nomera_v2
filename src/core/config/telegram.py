from pydantic_settings import BaseSettings


class TelegramSettings(BaseSettings):
    bot_token: str = "your_bot_token"
    admin_ids: list[int] = [123456789]
