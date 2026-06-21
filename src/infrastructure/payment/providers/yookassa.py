from decimal import Decimal
from typing import Any

from src.application.ports.payment.provider import PaymentProvider
from src.domain.entities.payment import Payment


class YooKassaProvider(PaymentProvider):
    """TODO: подключить YooKassa SDK когда будут готовы реквизиты магазина."""

    async def create_invoice(self, **kwargs: Any) -> dict:
        raise NotImplementedError("YooKassa провайдер пока не подключён")

    async def get_payment_instructions(self, payment: Payment) -> dict:
        raise NotImplementedError("YooKassa провайдер пока не подключён")