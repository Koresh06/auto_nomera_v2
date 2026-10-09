from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram_dialog import DialogManager
from dishka import AsyncContainer

from src.application.mediator import Mediator
from src.core.config import settings
from src.presentation.telegram.features.admin.modules.menu.filter import (
    is_admin_user,
)


class AdminDialogGuardMiddleware(BaseMiddleware):
    """Проверка прав на КАЖДОЕ действие внутри админских диалогов.

    /admin защищён AdminFilter только на входе. Если у админа сняли права
    (или его заменили в конфиге), уже открытый админ-диалог оставался
    полностью рабочим: можно было менять балансы, блокировать, назначать
    админов. Вешается inner-middleware на сами админские Dialog — к этому
    моменту aiogram-dialog уже загрузил контекст, а пользовательские
    диалоги проверка не затрагивает."""

    def __init__(self, *, super_admin_only: bool = False) -> None:
        # Разделы супер-админа (балансы, блокировки, назначение админов,
        # регионы, цены услуг) — только для админов из конфига. Назначенные
        # через бота админы видят урезанное меню, но скрытая кнопка меню всё
        # равно открывала раздел по подделанному нажатию.
        self._super_admin_only = super_admin_only

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        container: AsyncContainer | None = data.get("dishka_container")
        if user is None or container is None:
            return await handler(event, data)

        if self._super_admin_only:
            allowed = user.id in settings.telegram.admin_ids
        else:
            mediator: Mediator = await container.get(Mediator)
            allowed = await is_admin_user(user.id, mediator)
        if allowed:
            return await handler(event, data)

        manager: DialogManager | None = data.get("dialog_manager")
        if manager is not None:
            await manager.reset_stack()
        if isinstance(event, CallbackQuery):
            await event.answer("⛔ Доступ к админ-панели закрыт.", show_alert=True)
        elif isinstance(event, Message):
            await event.answer("⛔ Доступ к админ-панели закрыт.")
        return None
