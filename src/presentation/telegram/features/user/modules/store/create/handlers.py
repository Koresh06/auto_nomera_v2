from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from src.application.dtos.ad import AdDTO
from src.domain.value_objects.contacts import Contacts
from src.application.mediator import Mediator
from src.application.use_cases.store.create import CreateStoreRequest
from src.application.exceptions.store import StoreAlreadyExistsException


@inject
async def on_finish(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    user_id: int = data["user_id"]
    region_id: int = data["region_id"]
    username: str | None = data.get("username")

    contacts = Contacts.from_user(username=username, phone=data["phone"])

    try:
        store: AdDTO = await mediator.handle(
            CreateStoreRequest(
                user_id=user_id,
                region_id=region_id,
                shop_name=data["shop_name"],
                city=data["city"],
                contacts=contacts,
            )
        )
    except StoreAlreadyExistsException:
        await callback.answer("⚠️ У вас уже есть магазин.", show_alert=True)
        await dialog_manager.done()
        return

    dialog_manager.dialog_data["ad_id"] = store.id
    await dialog_manager.next()