from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from aiogram import Bot
from aiogram.types import LabeledPrice

from src.application.ports.payment.provider import PaymentProvider
from src.domain.entities.payment import Payment


@dataclass
class TelegramStarsProvider(PaymentProvider):
    bot: Bot
    xtr_to_rub_rate: Decimal

    async def create_invoice(
        self,
        *,
        user_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        external_id: str,
        **kwargs,
    ) -> dict:
        stars = int(
            (amount / self.xtr_to_rub_rate).to_integral_value(rounding=ROUND_CEILING)
        )

        invoice_link = await self.bot.create_invoice_link(
            title=description or "Оплата",
            description=description or "Оплата через Telegram Stars",
            payload=external_id,
            currency="XTR",
            prices=[LabeledPrice(label="XTR", amount=stars)],
        )

        return {
            "invoice_link": invoice_link,
            "stars_amount": stars,
            "exchange_rate": str(self.xtr_to_rub_rate),
        }

    async def get_payment_instructions(self, payment: Payment) -> dict:
        return {"type": "deeplink", "url": payment.meta.get("invoice_link")}

    async def handle_webhook(self, payload: dict) -> str | None:
        return payload.get("payload")
