import logging
from dishka.integrations.aiogram_dialog import inject
from dishka.integrations.aiogram import FromDishka
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Select
from aiogram_dialog.widgets.kbd.select import OnItemClick

from src.application.exceptions.user import UserAlreadyExistsException
from src.application.mediator import Mediator
from src.application.use_cases.user.register_user import UserRegisterRequest
from src.presentation.telegram.features.user.dialogs.start.states import StartSG


logger = logging.getLogger(__name__)


@inject
async def on_register_user(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
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
        await dialog_manager.switch_to(StartSG.menu)
    except UserAlreadyExistsException as ex:
        logger.info(str(ex))
        await callback.message.answer("Ошибка регистрации, обратитесь в поддержку!")
