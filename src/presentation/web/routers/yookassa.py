import logging

from fastapi import APIRouter, Request, HTTPException
from dishka.integrations.fastapi import inject, FromDishka

from src.application.ports.tasks.task_queue import TaskQueue
from src.application.services.payment.provider_registry import PaymentProviderRegistry
from src.domain.enums.payment import PaymentMethod
from src.infrastructure.payment.providers.yookassa import YooKassaProvider


logger = logging.getLogger(__name__)


router = APIRouter()


async def process_yookassa_webhook(
    payload: dict,
    *,
    task_queue: TaskQueue,
    provider_registry: PaymentProviderRegistry,
) -> dict:
    """Основная логика обработки webhook'а, вынесена отдельно от FastAPI-роута,
    чтобы её можно было протестировать без заворота dishka/Request.
    """
    obj = payload.get("object", {})
    yookassa_payment_id = obj.get("id")

    logger.info(
        f"[YooKassa:webhook:received] event={payload.get('event')} "
        f"payment_id={yookassa_payment_id}"
    )

    if not yookassa_payment_id:
        logger.error("[YooKassa:webhook] no payment id in payload object")
        raise HTTPException(status_code=400, detail="Invalid payload")

    provider = provider_registry.get(PaymentMethod.YOOKASSA)
    if not isinstance(provider, YooKassaProvider):
        # Защита от рассинхрона DI-конфигурации, не ожидается в проде.
        logger.error("[YooKassa:webhook] YOOKASSA provider is misconfigured")
        raise HTTPException(status_code=500, detail="Provider misconfigured")

    # НИКОГДА не доверяем event/status из тела запроса — YooKassa не подписывает
    # webhook, так что его тело может отправить кто угодно, кто знает payment_id
    # (например, свой собственный external_id из URL возврата). Запрашиваем
    # актуальный статус напрямую у YooKassa по нашему secret_key.
    verified = await provider.verify_payment(yookassa_payment_id=yookassa_payment_id)
    if verified is None:
        # Транзиентная ошибка похода в YooKassa API — просим прислать webhook
        # повторно, а не притворяемся, что обработали.
        raise HTTPException(status_code=502, detail="Could not verify payment")

    external_id = (verified.metadata or {}).get("external_id")
    if not external_id:
        logger.error(
            f"[YooKassa:webhook] verified payment {yookassa_payment_id} has no "
            "external_id in metadata"
        )
        raise HTTPException(status_code=400, detail="Invalid metadata")

    logger.info(
        f"[YooKassa:webhook:verified] payment_id={yookassa_payment_id} "
        f"external_id={external_id} verified_status={verified.status} "
        f"verified_paid={verified.paid}"
    )

    if verified.status == "succeeded" and verified.paid:
        await task_queue.enqueue(
            task_name="confirm_payment",
            args=(external_id,),
        )
        logger.info(f"[YooKassa:webhook:queued] external_id={external_id}")

    elif verified.status == "canceled":
        cancellation = obj.get("cancellation_details", {})
        logger.warning(
            f"[YooKassa:webhook:canceled] external_id={external_id} "
            f"reason={cancellation.get('reason')} party={cancellation.get('party')}"
        )
        await task_queue.enqueue(
            task_name="mark_payment_failed",
            args=(external_id,),
        )
    else:
        logger.info(
            f"[YooKassa:webhook:ignored] external_id={external_id} "
            f"verified_status={verified.status}"
        )

    return {"status": "ok"}


@router.post("/webhook/yookassa")
@inject
async def yookassa_webhook(
    request: Request,
    task_queue: FromDishka[TaskQueue],
    provider_registry: FromDishka[PaymentProviderRegistry],
) -> dict:
    payload = await request.json()
    return await process_yookassa_webhook(
        payload, task_queue=task_queue, provider_registry=provider_registry
    )
