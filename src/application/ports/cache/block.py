from typing import Protocol


class BlockCache(Protocol):
    async def get_flags(self, tg_id: int) -> tuple[bool, bool] | None:
        """Возвращает (is_blocked, is_payment_blocked) или None если нет в кэше."""
        ...

    async def set_flags(
        self,
        tg_id: int,
        *,
        is_blocked: bool,
        is_payment_blocked: bool,
    ) -> None: ...

    async def invalidate(self, tg_id: int) -> None: ...
