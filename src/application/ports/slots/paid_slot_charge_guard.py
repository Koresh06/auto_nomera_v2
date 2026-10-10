from typing import Protocol

from src.domain.value_objects.slot_key import SlotKey


class PaidSlotChargeGuard(Protocol):
    """Короткая блокировка «пользователь + слот» на время списания: второй
    тап по той же кнопке не списывает деньги повторно."""

    async def try_acquire(self, user_id: int, slot: SlotKey) -> bool:
        """True — можно списывать; False — списание за этот слот только что
        уже было (двойной тап)."""
        ...

    async def release(self, user_id: int, slot: SlotKey) -> None:
        """Снимает блокировку: следующий выбор слота — новая покупка."""
        ...
