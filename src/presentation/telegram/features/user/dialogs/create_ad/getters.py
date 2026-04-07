from dishka.integrations.aiogram_dialog import inject
from dishka.integrations.aiogram import FromDishka
from aiogram_dialog import DialogManager

from src.application.dtos.calendar import CalendarDTO
from src.application.mediator import Mediator
from src.application.use_cases.slots.get_calendar import GetCalendarRequest


REGION_ID_DEV = 1


async def default_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    start_data = dialog_manager.start_data
    return {}


@inject
async def calendar_getter(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
):
    cal: CalendarDTO = await mediator.handle(
        GetCalendarRequest(region_id=REGION_ID_DEV)
    )
    # ожидаем: cal.slots -> list[dict] с ключами id/text/is_busy
    return {"slots": cal.slots}
