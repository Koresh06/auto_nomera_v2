import logging
from aiogram import Router, F
from aiogram.types import PreCheckoutQuery, Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from src.application.mediator import Mediator
from src.application.use_cases.payment.confirm import ConfirmPaymentRequest
from src.application.use_cases.payment.get_by_external_id import GetPaymentByExternalIdRequest
from src.domain.entities.payment import Payment
from src.domain.enums.payment import PaymentPurpose


logger = logging.getLogger(__name__)


router = Router()


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery) -> None:
    """Подтверждаем готовность принять оплату — обязательно для Telegram Stars."""
    await query.bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
@inject
async def process_successful_payment(
    message: Message,
    mediator: FromDishka[Mediator],
) -> None:
    """
    Обрабатывает успешную оплату через Telegram Stars.
    payload инвойса == external_id платежа.
    """
    successful_payment = message.successful_payment
    external_id = successful_payment.invoice_payload
    amount_xtr = successful_payment.total_amount
    currency = successful_payment.currency

    logger.info(
        f"[Stars:successful_payment] external_id={external_id} "
        f"amount={amount_xtr} currency={currency}"
    )

    try:
        await mediator.handle(ConfirmPaymentRequest(external_id=external_id))
        logger.info(f"[Stars:confirmed] external_id={external_id}")
        # Если есть телепортация — отдельное сообщение не нужно,
        # юзер сам увидит новый экран после switch_to
        payment: Payment = await mediator.handle(
            GetPaymentByExternalIdRequest(external_id=external_id)
        )
        if not payment.meta.get("return_state"):
            text = _build_success_text(payment.purpose)
            await message.answer(text)
    except Exception as e:
        logger.exception(f"[Stars:error] external_id={external_id} error={e}")
        await message.answer(
            "❌ Ошибка при подтверждении платежа. Свяжитесь с поддержкой."
        )


def _build_success_text(purpose: PaymentPurpose) -> str:
    match purpose:
        case PaymentPurpose.BALANCE_TOPUP:
            return "✨ Баланс пополнен!"
        case PaymentPurpose.PUBLICATION_SERVICE:
            return "✅ Услуга подключена и применена!"
        case PaymentPurpose.PRE_PUBLICATION:
            return "💎 Подписка на ранний доступ активирована!"
        case PaymentPurpose.SLOT:
            return "📅 Слот оплачен!"
        case _:
            return "✅ Платёж подтверждён!"