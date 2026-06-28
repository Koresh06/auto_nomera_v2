from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import FromDishka, inject

from src.application.dtos.region import RegionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.domain.value_objects.contacts import Contacts


@inject
async def getter_current_region_user(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    region: RegionDTO = await mediator.handle(IdRegionRequest(user.region_id))

    dialog_manager.dialog_data["user_id"] = user.id
    dialog_manager.dialog_data["region_id"] = user.region_id
    dialog_manager.dialog_data["username"] = user.username

    return {"region_name": region.title}


@inject
async def getter_finish_store(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    name = dialog_manager.find("name").get_value()
    city = dialog_manager.find("city").get_value()
    phone = dialog_manager.dialog_data.get("phone") or dialog_manager.dialog_data.get("current_phone")
    username = dialog_manager.dialog_data.get("username")

    dialog_manager.dialog_data["shop_name"] = name
    dialog_manager.dialog_data["city"] = city
    dialog_manager.dialog_data["phone"] = phone

    contacts = Contacts.from_user(username=username, phone=phone)

    return {
        "shop_name": name,
        "city": city,
        "contacts": contacts.display,
    }