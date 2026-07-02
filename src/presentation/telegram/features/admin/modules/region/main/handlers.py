from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button

from src.application.mediator import Mediator
from src.application.use_cases.region.toggle_status import ToggleRegionStatusCommand
from src.presentation.telegram.features.admin.modules.region.edit.states import EditRegionMetadataSG, EditRegionSettingsSG


async def on_region_selected(
    callback: CallbackQuery,
    widget,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["region_id"] = int(item_id)
    await dialog_manager.next()


@inject
async def on_toggle_status(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    region_id: int = dialog_manager.dialog_data["region_id"]

    if not dialog_manager.dialog_data.get("toggle_confirm_pending"):
        dialog_manager.dialog_data["toggle_confirm_pending"] = True
        await callback.answer(
            "⚠️ Нажмите ещё раз, чтобы подтвердить смену статуса",
            show_alert=True,
        )
        await dialog_manager.show(show_mode=ShowMode.EDIT)
        return

    dialog_manager.dialog_data["toggle_confirm_pending"] = False
    await mediator.handle(ToggleRegionStatusCommand(region_id=region_id))
    await callback.answer("✅ Статус региона изменён")
    await dialog_manager.show(show_mode=ShowMode.EDIT)


async def on_open_edit_settings(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    region_id: int = dialog_manager.dialog_data["region_id"]
    await dialog_manager.start(
        EditRegionSettingsSG.menu,
        data={"region_id": region_id},
    )


async def on_open_edit_metadata(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    region_id: int = dialog_manager.dialog_data["region_id"]
    await dialog_manager.start(
        EditRegionMetadataSG.menu,
        data={"region_id": region_id},
    )