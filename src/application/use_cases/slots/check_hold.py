from dataclasses import dataclass

from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, eq=False)
class CheckHoldRequest(UseCaseRequest):
    region_id: int
    slot: SlotKey
    user_id: int


@dataclass(kw_only=True)
class CheckHoldUseCase(UseCase[CheckHoldRequest, bool]):
    hold_store: SlotHoldStore

    async def __call__(self, command: CheckHoldRequest) -> bool:
        return await self.hold_store.exists_for_user(
            slot=command.slot,
            user_id=command.user_id,
        )