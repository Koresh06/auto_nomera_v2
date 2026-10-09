from aiogram import Dispatcher
from dishka import AsyncContainer

from src.presentation.telegram.features import (
    get_admin_dialogs,
    get_super_admin_dialogs,
)
from src.presentation.telegram.middlewares.admin_guard import (
    AdminDialogGuardMiddleware,
)
from src.presentation.telegram.middlewares.block import BlockCheckMiddleware


def setup_middlewares(
    dp: Dispatcher,
    container: AsyncContainer,
) -> None:
    dp.update.outer_middleware(BlockCheckMiddleware())

    super_only = {id(d) for d in get_super_admin_dialogs()}
    admin_guard = AdminDialogGuardMiddleware()
    super_guard = AdminDialogGuardMiddleware(super_admin_only=True)
    for dialog in get_admin_dialogs():
        guard = super_guard if id(dialog) in super_only else admin_guard
        dialog.message.middleware(guard)
        dialog.callback_query.middleware(guard)
