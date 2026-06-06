from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.slots.slot_reservation_service import (
    HoldResult,
    SlotReservationService,
)
from src.domain.value_objects.slot_key import SlotKey
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class HoldSlotRequest(UseCaseRequest):
    region_id: int
    slot: SlotKey
    user_id: int
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class HoldSlotUseCase(UseCase[HoldSlotRequest, HoldResult]):
    region_repo: RegionRepository
    calendar_builder: CalendarBuilder
    reservation_service: SlotReservationService
    transaction_manager: TransactionManager

    async def __call__(self, command: HoldSlotRequest) -> HoldResult:
        now = command.now_utc or datetime.now(timezone.utc)
        region = await self.region_repo.get_by_id(command.region_id)

        ordered_future_slots = self.calendar_builder.generate_future_slots(
            region=region,
            now_utc=now,
        )

        result = await self.reservation_service.hold_slot(
            slot=command.slot,
            user_id=command.user_id,
            ordered_future_slots=ordered_future_slots,
            now_utc=now,
        )
        await self.transaction_manager.commit()

        return result
