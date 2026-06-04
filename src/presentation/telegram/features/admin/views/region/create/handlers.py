from dishka.integrations.aiogram import FromDishka
from dishka.integrations.aiogram_dialog import inject
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from src.application.mediator import Mediator
from src.application.use_cases.region.create import CreateRegionCommand


@inject
async def on_confirm_region(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    title = dialog_manager.find("title").get_value()
    timezone = dialog_manager.find("timezone").get_value()
    channel_id = dialog_manager.find("channel_id").get_value()
    channel_username = dialog_manager.find("channel_username").get_value()

    try:
        await mediator.handle(
            CreateRegionCommand(
                title=title,
                timezone=timezone,
                channel_id=channel_id,
                channel_username=channel_username,
            )
        )
    except Exception as e:
        await callback.answer(str(e))
        print(e)
    else:
        await callback.answer("Регион успешно создан!")


    await dialog_manager.done()