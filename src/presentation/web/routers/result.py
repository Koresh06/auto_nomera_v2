from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dishka.integrations.fastapi import inject, FromDishka

from src.core.config import settings
from src.domain.entities.payment import Payment, PaymentStatus
from src.application.mediator import Mediator
from src.application.use_cases.payment.get_by_external_id import (
    GetPaymentByExternalIdRequest,
)

templates = Jinja2Templates(directory="src/presentation/web/templates")


router = APIRouter()


@router.get("/payment/return", response_class=HTMLResponse)
@inject
async def payment_return(
    request: Request,
    mediator: FromDishka[Mediator],
    external_id: str | None = None,
) -> HTMLResponse:
    ctx = {"bot_url": settings.telegram.bot_url}

    if not external_id:
        return templates.TemplateResponse(request, "cancel.html", ctx)

    try:
        payment: Payment = await mediator.handle(
            GetPaymentByExternalIdRequest(external_id=external_id)
        )
    except Exception:
        return templates.TemplateResponse(request, "cancel.html", ctx)

    if payment.status in (PaymentStatus.PAID, PaymentStatus.WAITING_CONFIRMATION):
        return templates.TemplateResponse(request, "success.html", ctx)

    if payment.status == PaymentStatus.PENDING:
        return templates.TemplateResponse(request, "pending.html", ctx)

    return templates.TemplateResponse(request, "cancel.html", ctx)
