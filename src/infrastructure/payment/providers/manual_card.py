import secrets
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.application.ports.payment.provider import PaymentProvider
from src.domain.entities.payment import Payment


@dataclass
class ManualCardProvider(PaymentProvider):
    card: str

    async def create_invoice(
        self,
        *,
        user_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        external_id: str,
        **kwargs: Any,
    ) -> dict:
        reference = secrets.token_hex(4).upper()
        return {"card": self.card, "reference": reference}

    async def get_payment_instructions(self, payment: Payment) -> dict:
        return {
            "type": "text_instructions",
            "card": payment.meta.get("card"),
            "reference": payment.meta.get("reference"),
            "instructions": (
                f"Переведите {payment.amount} руб. на карту {payment.meta.get('card')}.\n"
                f"В комментарии укажите код {payment.meta.get('reference')}.\n"
                "После перевода отправьте номер операции или чек — администратор подтвердит оплату."
            ),
        }