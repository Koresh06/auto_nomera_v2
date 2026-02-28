from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram_dialog import DialogManager, StartMode
from dishka.integrations.aiogram import FromDishka, inject

from src.application.mediator import Mediator
from src.application.use_cases.user.register_user import UserRegisterRequest
from src.presentation.telegram.features.user.dialogs.create_ad.states import CreateAdSG


router = Router()


@router.message(CommandStart())
@inject
async def process_start_command(
    message: Message,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    await mediator.handle(
            UserRegisterRequest(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
    )
    await dialog_manager.start(
        CreateAdSG.plate,
        mode=StartMode.RESET_STACK,
    )
