from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import ManagedTextInput

from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.store.update_store import UpdateStoreRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.value_objects.contacts import Contacts

from .states import StoreEditSG


async def on_next_confirm(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
) -> None:
    widget_id = widget.widget.widget_id
    if widget_id == "name":
        dialog_manager.dialog_data["new_name"] = value
    elif widget_id == "city":
        dialog_manager.dialog_data["new_city"] = value
    elif widget_id == "phone":
        dialog_manager.dialog_data["new_phone"] = value

    await dialog_manager.switch_to(StoreEditSG.confirm)


@inject
async def on_confirm_edit(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    ad_id: int = data["ad_id"]
    new_name = data.get("new_name")
    new_city = data.get("new_city")
    new_phone = data.get("new_phone")

    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=callback.from_user.id))

    contacts = (
        Contacts.from_user(
            username=user.username,
            phone=new_phone,
        )
        if new_phone
        else None
    )

    await mediator.handle(
        UpdateStoreRequest(
            ad_id=ad_id,
            shop_name=new_name,
            city=new_city,
            contacts=contacts,
        )
    )

    await callback.answer("✅ Магазин обновлён!", show_alert=True)
    await dialog_manager.done()
