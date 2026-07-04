import logging

from fastapi import APIRouter, Request, HTTPException
from dishka.integrations.fastapi import inject, FromDishka

from src.application.ports.tasks.task_queue import TaskQueue


logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/webhook/yookassa")
@inject
async def yookassa_webhook(
    request: Request,
    task_queue: FromDishka[TaskQueue],
) -> dict:
    payload = await request.json()

    event = payload.get("event")
    obj = payload.get("object", {})
    metadata = obj.get("metadata", {})
    external_id = metadata.get("external_id")

    logger.info(
        f"[YooKassa:webhook] event={event} payment_id={obj.get('id')} "
        f"status={obj.get('status')} external_id={external_id}"
    )

    if not external_id:
        logger.error(f"[YooKassa:webhook] no external_id in metadata: {metadata}")
        raise HTTPException(status_code=400, detail="Invalid metadata")

    if event == "payment.succeeded":
        await task_queue.enqueue(
            task_name="confirm_payment",
            args=(external_id,),
        )
        logger.info(f"[YooKassa:webhook:queued] external_id={external_id}")

    elif event == "payment.canceled":
        cancellation = obj.get("cancellation_details", {})
        logger.warning(
            f"[YooKassa:webhook:canceled] external_id={external_id} "
            f"reason={cancellation.get('reason')} party={cancellation.get('party')}"
        )
        await task_queue.enqueue(
            task_name="mark_payment_failed",
            args=(external_id,),
        )

    return {"status": "ok"}
