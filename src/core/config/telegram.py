from pydantic_settings import BaseSettings


class TelegramSettings(BaseSettings):
    bot_token: str = "your_bot_token"
    bot_url: str = "https://t.me/your_bot"
    admin_ids: list[int] = [123456789]
