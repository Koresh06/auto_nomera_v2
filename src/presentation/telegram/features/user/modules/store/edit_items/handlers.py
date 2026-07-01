from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd.select import OnItemClick
from aiogram_dialog.widgets.kbd import  Select, Button
from aiogram_dialog.widgets.input import ManagedTextInput

from src.application.dtos.ad import AdDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.store.delete_items import DeleteStoreItemRequest
from src.application.use_cases.store.update_items import UpdateStoreItemRequest
from src.domain.services.ad.plate_validator import validate_plate
from src.presentation.telegram.utils.price_validators import validate_price
from src.presentation.telegram.features.user.modules.store.edit_item.states import StoreEditItemsSG


@inject
async def on_edit_item_selected(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    ad_id: int = data["ad_id"]

    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))
    s = ad.store_content

    data["selected_plate"] = item_id
    data["new_plate"] = None
    data["new_price"] = None
    data["new_price_display"] = None

    if s:
        for item in s.items:
            if item.plate == item_id:
                data["selected_price_display"] = item.price.display
                data["selected_price_value"] = item.price.value
                break

    await dialog_manager.switch_to(StoreEditItemsSG.edit)


async def on_plate_input(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
) -> None:
    try:
        plate = validate_plate(value, allow_mask=False)
    except ValueError as e:
        await message.answer(str(e))
        return
    dialog_manager.dialog_data["new_plate"] = plate
    dialog_manager.dialog_data["new_price_display"] = None
    await dialog_manager.switch_to(StoreEditItemsSG.confirm)


async def on_price_input(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
) -> None:
    try:
        validated = validate_price(value)
    except ValueError as e:
        await message.answer(str(e))
        return
    dialog_manager.dialog_data["new_price"] = value
    dialog_manager.dialog_data["new_price_display"] = validated
    dialog_manager.dialog_data["new_plate"] = None
    await dialog_manager.switch_to(StoreEditItemsSG.confirm)


@inject
async def on_delete_item(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    ad_id: int = data["ad_id"]
    plate: str = data["selected_plate"]

    await mediator.handle(
        DeleteStoreItemRequest(ad_id=ad_id, plate=plate)
    )

    await callback.answer("✅ Номер удалён.", show_alert=True)
    await dialog_manager.switch_to(StoreEditItemsSG.all_list)


@inject
async def on_confirm_update(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    ad_id: int = data["ad_id"]
    plate: str = data["selected_plate"]
    new_plate: str | None = data.get("new_plate")
    new_price: int | None = data.get("new_price")

    await mediator.handle(
        UpdateStoreItemRequest(
            ad_id=ad_id,
            plate=plate,
            new_plate=new_plate,
            new_price=new_price,
        )
    )

    if new_plate:
        data["selected_plate"] = new_plate

    await callback.answer("✅ Изменения сохранены.", show_alert=True)
    await dialog_manager.switch_to(StoreEditItemsSG.edit)