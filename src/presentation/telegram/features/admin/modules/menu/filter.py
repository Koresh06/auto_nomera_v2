from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from dishka.integrations.aiogram import inject, FromDishka

from src.domain.enums.role import UserRole
from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest


class AdminFilter(BaseFilter):
    def __init__(self, admin_ids: list[int]):
        self.bootstrap_admins = set(admin_ids)

    async def is_admin(self, tg_id: int, mediator: Mediator) -> bool:
        """Основная логика, вынесена из __call__ (который dishka оборачивает
        через @inject и требует контейнер в kwargs) — чтобы её можно было
        протестировать без заворота dishka/aiogram.
        """
        if tg_id in self.bootstrap_admins:
            return True

        try:
            user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id))
        except UserNotFoundException:
            return False

        return user.role == UserRole.ADMIN

    @inject
    async def __call__(
        self,
        event: Message | CallbackQuery,
        mediator: FromDishka[Mediator],
        **kwargs,
    ) -> bool:
        return await self.is_admin(event.from_user.id, mediator)


async def is_admin_user(tg_id: int, mediator: Mediator) -> bool:
    """Проверка прав администратора для хендлеров вне админского роутера.

    Видимость кнопки (``when=``) в aiogram-dialog НЕ является защитой:
    скрытые кнопки всё равно обрабатывают callback, а callback_data
    модифицированный клиент может прислать любую. Поэтому действия с
    правами проверяются здесь, на сервере."""
    from src.core.config import settings

    return await AdminFilter(settings.telegram.admin_ids).is_admin(tg_id, mediator)
