import asyncio
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from yookassa import Configuration, Payment as YooKassaPayment
from yookassa.domain.response import PaymentResponse

from src.application.dtos.yookassa import YooKassaInvoiceRequest, YooKassaReceiptItem
from src.application.ports.payment.provider import PaymentProvider
from src.core.config.payment import YooKassaSettings
from src.domain.entities.payment import Payment


logger = logging.getLogger(__name__)


@dataclass
class YooKassaProvider(PaymentProvider):
    account_id: int
    secret_key: str
    settings: YooKassaSettings

    def __post_init__(self) -> None:
        Configuration.account_id = self.account_id
        Configuration.secret_key = self.secret_key

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
        phone: str = kwargs.get("phone", "")
        chat_id: int = kwargs.get("chat_id", user_id)

        return_url = return_url = (
            f"{self.settings.return_url}?external_id={external_id}"
        )

        invoice_request = YooKassaInvoiceRequest(
            amount=amount,
            description=description,
            return_url=return_url,
            external_id=external_id,
            user_id=user_id,
            chat_id=chat_id,
            phone=phone,
            receipt_items=[
                YooKassaReceiptItem(
                    description=description,
                    quantity=Decimal("1.00"),
                    unit_price=amount,
                )
            ],
        )

        idempotence_key = str(uuid.uuid4())
        logger.info("BEFORE YOOKASSA CREATE")

        try:
            response: PaymentResponse = await asyncio.wait_for(
                asyncio.to_thread(
                    YooKassaPayment.create,
                    invoice_request.to_dict(),
                    idempotence_key,
                ),
                timeout=15,
            )
        except asyncio.TimeoutError:
            logger.exception("YOOKASSA TIMEOUT")
            raise
        except Exception:
            logger.exception("YOOKASSA ERROR")
            raise

        logger.info("AFTER YOOKASSA CREATE: %s", response.id)

        return {
            "yookassa_payment_id": response.id,
            "confirmation_url": response.confirmation.confirmation_url,
        }

    async def get_payment_instructions(self, payment: Payment) -> dict:
        return {
            "type": "deeplink",
            "url": payment.meta.get("confirmation_url"),
        }

    async def handle_webhook(self, payload: dict) -> str | None:
        obj = payload.get("object", {})
        metadata = obj.get("metadata", {})
        return metadata.get("external_id")
