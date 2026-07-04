from dataclasses import dataclass
from typing import Any

from src.application.ports.payment.provider import PaymentProvider
from src.domain.entities.payment import Payment


@dataclass
class CryptomusProvider(PaymentProvider):
    """TODO: подключить Cryptomus API когда будет готов аккаунт/ключи."""

    async def create_invoice(self, **kwargs: Any) -> dict:
        raise NotImplementedError("Cryptomus провайдер пока не подключён")

    async def get_payment_instructions(self, payment: Payment) -> dict:
        raise NotImplementedError("Cryptomus провайдер пока не подключён")
