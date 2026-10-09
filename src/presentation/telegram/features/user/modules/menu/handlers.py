import logging
from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Select
from aiogram_dialog.widgets.kbd.select import OnItemClick

from src.application.dtos.user import UpdateUserDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.exceptions.user import UserAlreadyExistsException
from src.domain.exceptions.region import RegionDisabledError
from src.application.mediator import Mediator
from src.application.use_cases.user.register import UserRegisterRequest
from src.application.use_cases.user.update import UpdateUserRequest
from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG


logger = logging.getLogger(__name__)


@inject
async def register_user_or_change_region(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    try:
        await _register_or_change_region(callback, item_id, mediator)
    except (RegionDisabledError, RegionNotFoundException):
        # регион отключили, пока пользователь смотрел список
        await callback.answer(
            "⚠️ Этот регион сейчас недоступен. Выберите другой.", show_alert=True
        )
        return

    await dialog_manager.start(
        UserMenuSG.menu,
        mode=StartMode.RESET_STACK,
    )


async def _register_or_change_region(
    callback: CallbackQuery, item_id: str, mediator: Mediator
) -> None:
    try:
        await mediator.handle(
            UserRegisterRequest(
                tg_id=callback.from_user.id,
                region_id=int(item_id),
                username=callback.from_user.username,
                full_name=callback.from_user.full_name,
            )
        )
        logger.info(
            f"Регистрация пользователя tg_id: {callback.from_user.id} успешно завершена!"
        )
    except UserAlreadyExistsException:
        await mediator.handle(
            UpdateUserRequest(
                tg_id=callback.from_user.id,
                data=UpdateUserDTO(region_id=int(item_id)),
            )
        )
        logger.info(
            f"Смена региона пользователя tg_id: {callback.from_user.id} на region_id={item_id}"
        )
