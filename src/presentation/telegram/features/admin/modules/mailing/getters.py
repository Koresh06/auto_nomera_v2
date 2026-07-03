from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.mediator import Mediator
from src.application.use_cases.region.get_all import GetRegionsRequest
from src.domain.enums.miling import MailingType


@inject
async def regions_getter(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    regions = await mediator.handle(GetRegionsRequest())
    return {"regions": regions}


async def mailing_confirm_getter(
    dialog_manager: DialogManager,
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    mail_type = MailingType(data["mail_type"])

    region_display = ""
    if mail_type == MailingType.TO_REGION:
        region_display = f"📍 Регион: {data.get('region_title', data.get('region_id'))}"

    return {
        "mail_type_display": mail_type.label(),
        "region_display": region_display,
    }