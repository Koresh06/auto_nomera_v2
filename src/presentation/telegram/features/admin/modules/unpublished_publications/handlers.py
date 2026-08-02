from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select

from src.application.mediator import Mediator
from src.application.use_cases.publication.publish_overdue_batch import (
    PublishOverdueBatchRequest,
    BatchResult,
)

from src.presentation.telegram.features.admin.modules.unpublished_publications.states import (
    UnpublishedAdsSG,
)


async def on_pick_slot(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["selected_slot"] = item_id
    await dialog_manager.next()


@inject
async def getter_unpublished_by_slot(
    dialog_manager: DialogManager,
    **kwargs,
) -> dict:
    slot = dialog_manager.dialog_data["selected_slot"]
    all_items = dialog_manager.dialog_data.get("overdue_items", [])
    filtered = [i for i in all_items if i["local_time_label"] == slot]

    return {
        "ads": filtered,
        "has_ads": bool(filtered),
        "count": len(filtered),
        "slot": slot,
    }


@inject
async def on_publish_all(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    slot = dialog_manager.dialog_data["selected_slot"]
    all_items = dialog_manager.dialog_data.get("overdue_items", [])
    pub_ids = [i["publication_id"] for i in all_items if i["local_time_label"] == slot]

    result: BatchResult = await mediator.handle(
        PublishOverdueBatchRequest(publication_ids=pub_ids)
    )

    text = f"✅ Опубликовано: {result.success}"
    if result.failed:
        text += f"\n❌ Ошибок: {len(result.failed)}"

    await callback.answer(text, show_alert=True)
    await dialog_manager.switch_to(UnpublishedAdsSG.pick_slot)
