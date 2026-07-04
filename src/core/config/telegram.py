from pydantic_settings import BaseSettings


class TelegramSettings(BaseSettings):
    bot_token: str = "your_bot_token"
    bot_proxy: str = "socks5://127.0.0.1:1080"
    admin_ids: list[int] = [123456789]
    bot_url: str = "https://t.me/your_bot"
    buyout_url: str = "https://t.me/your_buyout_bot"
