from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import ManagedTextInput

from src.application.mediator import Mediator
from src.application.use_cases.region.update_metadata import UpdateRegionMetadataCommand
from src.presentation.telegram.features.admin.modules.region.edit.states import EditRegionMetadataSG


@inject
async def on_metadata_confirm(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    tg_group_url = data["tg_group_url"]
    vk_group_url = data["vk_group_url"]
    max_channel_url = data["max_channel_url"]
    await mediator.handle(
        UpdateRegionMetadataCommand(
            region_id=dialog_manager.dialog_data["region_id"],
            tg_group_url=tg_group_url or None,
            vk_group_url=vk_group_url or None,
            max_channel_url=max_channel_url or None,
        )
    )
    await callback.answer("✅ Ссылки сохранены")
    await dialog_manager.done()


async def on_metadata_url_success(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    value: str,
) -> None:
    field_map = {
        "tg_input": "tg_group_url",
        "vk_input": "vk_group_url",
        "max_input": "max_channel_url",
    }
    field = field_map[widget.widget_id]
    dialog_manager.dialog_data[field] = "" if value == "-" else value
    await dialog_manager.switch_to(EditRegionMetadataSG.menu)