from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput

from src.application.mediator import Mediator
from src.application.use_cases.region.update_metadata import UpdateRegionMetadataCommand
from src.presentation.telegram.features.admin.modules.region.edit.states import EditRegionMetadataSG


_FIELD_BY_WIDGET = {
    "tg_input": "tg_group_url",
    "vk_input": "vk_group_url",
    "max_input": "max_channel_url",
}


@inject
async def on_metadata_url_success(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    field = _FIELD_BY_WIDGET[widget.widget.widget_id]
    new_value = None if value == "-" else value

    region_id: int = dialog_manager.start_data["region_id"]
    await mediator.handle(
        UpdateRegionMetadataCommand(region_id=region_id, **{field: new_value})
    )
    await message.answer("✅ Ссылка сохранена")
    await dialog_manager.switch_to(EditRegionMetadataSG.menu)