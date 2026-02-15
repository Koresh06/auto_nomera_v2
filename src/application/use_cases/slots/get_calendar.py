from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.dtos.calendar import CalendarDTO, CalendarSlotDTO
from src.application.dtos.slot_key_codec import encode_slot_key
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.services.slots.calendar_builder import CalendarBuilder


@dataclass(frozen=True, eq=False)
class GetCalendarRequest(UseCaseRequest):
    region_id: int
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class GetCalendarUseCase(UseCase[GetCalendarRequest, CalendarDTO]):
    region_repo: RegionRepository
    booking_repo: SlotBookingRepository
    converted_repo: SlotConvertedRepository
    hold_store: SlotHoldStore
    calendar_builder: CalendarBuilder

    async def __call__(self, command: GetCalendarRequest) -> CalendarDTO:
        now = command.now_utc or datetime.now(timezone.utc)
        region = await self.region_repo.get_by_id(command.region_id)

        future_slots = self.calendar_builder.generate_future_slots(region=region, now_utc=now)

        booked = await self.booking_repo.get_booked_set(future_slots)
        converted = await self.converted_repo.get_converted_set(future_slots)
        held = await self.hold_store.get_held_set(future_slots)

        views = self.calendar_builder.build(
            region=region,
            now_utc=now,
            held_slots=held,
            booked_slots=booked,
            converted_paid_slots=converted,
        )

        slots_dto = [
            CalendarSlotDTO(
                id=encode_slot_key(v.slot_key),
                text=v.text,
                slot=v.slot_key,
                availability=v.availability,
                pricing=v.pricing,
                disabled=v.is_disabled,
            )
            for v in views
        ]

        return CalendarDTO(region_id=command.region_id, slots=slots_dto)
