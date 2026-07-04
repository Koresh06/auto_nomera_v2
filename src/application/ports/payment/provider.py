from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from src.domain.entities.payment import Payment


class PaymentProvider(ABC):
    @abstractmethod
    async def create_invoice(
        self,
        *,
        user_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        external_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Возвращает meta для сохранения в Payment.meta."""
        ...

    @abstractmethod
    async def get_payment_instructions(self, payment: Payment) -> dict[str, Any]:
        """Что показать пользователю в боте."""
        ...

    async def handle_webhook(self, payload: dict[str, Any]) -> str | None:
        """Возвращает external_id для ConfirmPaymentUseCase."""
        return None
