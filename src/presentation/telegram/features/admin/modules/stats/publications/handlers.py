from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Select

from src.application.mediator import Mediator
from src.application.use_cases.publication.cancel_by_admin import (
    CancelPublicationByAdminRequest,
)


async def on_period_selected(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["period"] = button.widget_id
    await dialog_manager.show(show_mode=ShowMode.EDIT)


async def on_schedule_region_selected(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["region_id"] = int(item_id)
    await dialog_manager.next()


async def on_open_deferred_catalog(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    region_id: int = dialog_manager.dialog_data["region_id"]
    await dialog_manager.next()


@inject
async def on_delete_deferred(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    if not data.get("del_confirm"):
        data["del_confirm"] = True
        await callback.answer(
            "⚠️ Нажмите ещё раз для отмены публикации", show_alert=True
        )
        return

    data["del_confirm"] = False
    await mediator.handle(
        CancelPublicationByAdminRequest(
            publication_id=data["current_pub_id"],
            owner_tg_id=dialog_manager.event.from_user.id,
            label=data["current_label"],
        )
    )
    await callback.answer("✅ Публикация отменена")
    await dialog_manager.show(show_mode=ShowMode.EDIT)


async def on_catalog_item_selected(
    callback: CallbackQuery,
    button: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    idx = int(item_id)
    scroll = dialog_manager.find("catalog_scroll")
    if scroll:
        await scroll.set_page(callback, idx, dialog_manager)
    await dialog_manager.back()
