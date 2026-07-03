from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from dishka import AsyncContainer

from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.ports.cache.block import BlockCache
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest


class BlockCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        tg_id = user.id
        container: AsyncContainer = data["dishka_container"]
        cache: BlockCache = await container.get(BlockCache)

        flags = await cache.get_flags(tg_id)
        if flags is None:
            mediator: Mediator = await container.get(Mediator)
            try:
                dto: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))
            except UserNotFoundException:
                return await handler(event, data)
            flags = (dto.is_blocked, dto.is_payment_blocked)
            await cache.set_flags(
                tg_id,
                is_blocked=dto.is_blocked,
                is_payment_blocked=dto.is_payment_blocked,
            )

        is_blocked, is_payment_blocked = flags

        if is_blocked:
            text = "🚫 Вы заблокированы в этом боте."
            if isinstance(event, Update):
                if event.message:
                    await event.message.answer(text)
                elif event.callback_query:
                    await event.callback_query.answer(text, show_alert=True)
            return

        data["is_payment_blocked"] = is_payment_blocked
        return await handler(event, data)