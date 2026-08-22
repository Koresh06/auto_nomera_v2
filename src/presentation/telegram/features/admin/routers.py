import logging

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram_dialog import DialogManager, StartMode

from src.core.config import settings
from src.presentation.telegram.features.admin.modules.menu.filter import AdminFilter
from src.presentation.telegram.features.admin.modules.menu.states import AdminMenuSG

logger = logging.getLogger(__name__)


router = Router()


@router.message(
    Command("admin"),
    AdminFilter(settings.telegram.admin_ids),
)
async def process_command_admin(
    message: Message,
    dialog_manager: DialogManager,
):
    logger.info("Admin command received from %s", message.from_user.id)
    await dialog_manager.start(
        state=AdminMenuSG.menu,
        mode=StartMode.RESET_STACK,
    )
