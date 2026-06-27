from decimal import Decimal

from pydantic_settings import BaseSettings


class ManualCardSettings(BaseSettings):
    card_number: str = "0000 0000 0000 0000"


class TelegramStarsSettings(BaseSettings):
    xtr_to_rub_rate: Decimal = Decimal("1.65")


class YooKassaSettings(BaseSettings):
    account_id: int = 0
    secret_key: str = ""
    return_url: str = ""


class CryptomusSettings(BaseSettings):
    merchant_id: str = ""
    api_key: str = ""


class PaymentSettings(BaseSettings):
    manual_card: ManualCardSettings = ManualCardSettings()
    telegram_stars: TelegramStarsSettings = TelegramStarsSettings()
    yookassa: YooKassaSettings = YooKassaSettings()
    cryptomus: CryptomusSettings = CryptomusSettings()