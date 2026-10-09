import asyncio
import logging
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from yookassa import Configuration, Payment as YooKassaPayment
from yookassa.domain.response import PaymentResponse

from src.application.exceptions.payment import PaymentProviderUnavailableException
from src.application.dtos.yookassa import YooKassaInvoiceRequest, YooKassaReceiptItem
from src.application.ports.payment.provider import PaymentProvider
from src.core.config.payment import YooKassaSettings
from src.domain.entities.payment import Payment
from src.domain.enums.payment import PaymentMethod
from src.domain.exceptions.payment import PaymentPhoneRequiredException


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
        phone = re.sub(r"\D", "", kwargs.get("phone", "") or "")
        if not phone:
            raise PaymentPhoneRequiredException(PaymentMethod.YOOKASSA)

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
        except asyncio.TimeoutError as e:
            logger.exception("YOOKASSA TIMEOUT")
            raise PaymentProviderUnavailableException("yookassa") from e
        except Exception as e:
            # Сетевые сбои SDK ЮKassa всплывают невнятно (например, при ошибке
            # прокси — AttributeError: 'NoneType' object has no attribute
            # 'status_code'), поэтому любую ошибку вызова считаем
            # недоступностью провайдера: платёж не создан, можно повторить.
            logger.exception("YOOKASSA ERROR")
            raise PaymentProviderUnavailableException("yookassa") from e

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

    async def verify_payment(
        self, *, yookassa_payment_id: str
    ) -> PaymentResponse | None:
        """Серверная сверка статуса платежа напрямую через YooKassa API
        (авторизовано нашим secret_key), а НЕ доверие телу webhook-запроса.

        YooKassa не подписывает тело webhook'а, поэтому любой, кто знает
        payment_id/external_id (например, свой собственный из return_url),
        мог бы просто сам отправить POST с {"event": "payment.succeeded"} —
        без этой проверки платёж подтвердился бы без реального поступления
        денег. Здесь мы запрашиваем актуальный статус у самой YooKassa и
        доверяем только этому ответу.
        """
        try:
            response: PaymentResponse = await asyncio.wait_for(
                asyncio.to_thread(YooKassaPayment.find_one, yookassa_payment_id),
                timeout=15,
            )
        except asyncio.TimeoutError:
            logger.exception(
                "[YooKassa:verify_timeout] payment_id=%s", yookassa_payment_id
            )
            return None
        except Exception:
            logger.exception(
                "[YooKassa:verify_error] payment_id=%s", yookassa_payment_id
            )
            return None

        return response
