from dataclasses import dataclass

from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
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
    converted_repo: SlotConvertedRepository

    async def __call__(self, command: CheckHoldRequest) -> bool:
        hold_valid = await self.hold_store.exists_for_user(
            slot=command.slot,
            user_id=command.user_id,
        )
        if hold_valid:
            return True

        # слот может быть уже оплачен и сконвертирован этим юзером
        converted_owner_id = await self.converted_repo.get_converted_owner_and_ad(
            command.slot
        )
        return converted_owner_id == command.user_id