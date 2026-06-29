from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.exceptions.store import StoreItemsAlreadyExistException
from src.application.mediator import Mediator
from src.application.use_cases.store.add_items import AddStoreItemsRequest, AddStoreItemsResult
from src.domain.services.ad.store_validator import StoreInputParseResult
from src.domain.value_objects.price import Price
from src.domain.value_objects.store_content import StoreItem


async def on_input_submit(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: StoreInputParseResult,
) -> None:
    dialog_manager.dialog_data["parsed_items"] = [
        {
            "plate": item.plate,
            "price_value": item.price.value,
            "price_display": item.price.display,
        }
        for item in value.items
    ]
    dialog_manager.dialog_data["skipped_count"] = value.skipped_count
    await dialog_manager.next()


@inject
async def on_confirm_save(
    callback,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    ad_id: int = data["ad_id"]
    parsed_items: list[dict] = data.get("parsed_items", [])

    items = [
        StoreItem(plate=i["plate"], price=Price(i["price_value"]))
        for i in parsed_items
    ]

    try:
        result: AddStoreItemsResult = await mediator.handle(
            AddStoreItemsRequest(ad_id=ad_id, items=items)
        )
    except StoreItemsAlreadyExistException as e:
        await callback.answer(str(e), show_alert=True)
        return

    dialog_manager.dialog_data["added_count"] = result.added_count
    await dialog_manager.next()