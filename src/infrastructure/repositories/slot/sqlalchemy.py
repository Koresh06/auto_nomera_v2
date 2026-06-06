from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.domain.value_objects.slot_key import SlotKey
from src.infrastructure.database.models.slot import SlotBookingModel, SlotConvertedModel


class SQLAlchemySlotBookingRepo(SlotBookingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_booked(self, slot: SlotKey) -> bool:
        result = await self._session.execute(
            select(SlotBookingModel).where(
                SlotBookingModel.region_id == slot.region_id,
                SlotBookingModel.slot_day == slot.local_day,
                SlotBookingModel.slot_time == slot.local_time,
            )
        )
        return result.scalar_one_or_none() is not None

    async def book(self, slot: SlotKey, *, ad_id: int, user_id: int) -> None:
        model = SlotBookingModel(
            region_id=slot.region_id,
            slot_day=slot.local_day,
            slot_time=slot.local_time,
            ad_id=ad_id,
            user_id=user_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

    async def get_booked_set(self, slots: Iterable[SlotKey]) -> set[SlotKey]:
        slots_list = list(slots)
        if not slots_list:
            return set()

        result = await self._session.execute(
            select(
                SlotBookingModel.region_id,
                SlotBookingModel.slot_day,
                SlotBookingModel.slot_time,
            ).where(
                SlotBookingModel.region_id == slots_list[0].region_id,
                SlotBookingModel.slot_day.in_([s.local_day for s in slots_list]),
                SlotBookingModel.slot_time.in_([s.local_time for s in slots_list]),
            )
        )

        booked = {(row.region_id, row.slot_day, row.slot_time) for row in result.all()}

        return {
            slot
            for slot in slots_list
            if (slot.region_id, slot.local_day, slot.local_time) in booked
        }


class SQLAlchemySlotConvertedRepo(SlotConvertedRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_converted(self, slot: SlotKey) -> bool:
        result = await self._session.execute(
            select(SlotConvertedModel).where(
                SlotConvertedModel.region_id == slot.region_id,
                SlotConvertedModel.slot_day == slot.local_day,
                SlotConvertedModel.slot_time == slot.local_time,
            )
        )
        return result.scalar_one_or_none() is not None

    async def mark_converted(
        self,
        slot: SlotKey,
        *,
        user_id: int,
        ad_id: int | None = None,
    ) -> None:
        # INSERT ... ON CONFLICT DO NOTHING — идемпотентно
        stmt = (
            insert(SlotConvertedModel)
            .values(
                region_id=slot.region_id,
                slot_day=slot.local_day,
                slot_time=slot.local_time,
                ad_id=ad_id,
                user_id=user_id,
            )
            .on_conflict_do_nothing(
                index_elements=["region_id", "slot_day", "slot_time"]
            )
        )
        await self._session.execute(stmt)

    async def unmark_converted(self, slot: SlotKey, user_id: int) -> None:
        result = await self._session.execute(
            delete(SlotConvertedModel).where(
                SlotConvertedModel.region_id == slot.region_id,
                SlotConvertedModel.slot_day == slot.local_day,
                SlotConvertedModel.slot_time == slot.local_time,
                SlotConvertedModel.user_id == user_id,
            )
        )
        print(
            f"[unmark_converted] deleted {result} rows for slot={slot} user_id={user_id}"
        )

    async def get_converted_set(self, slots: Iterable[SlotKey]) -> set[SlotKey]:
        slots_list = list(slots)
        if not slots_list:
            return set()

        result = await self._session.execute(
            select(
                SlotConvertedModel.region_id,
                SlotConvertedModel.slot_day,
                SlotConvertedModel.slot_time,
            ).where(
                SlotConvertedModel.region_id == slots_list[0].region_id,
                SlotConvertedModel.slot_day.in_([s.local_day for s in slots_list]),
                SlotConvertedModel.slot_time.in_([s.local_time for s in slots_list]),
            )
        )

        converted = {
            (row.region_id, row.slot_day, row.slot_time) for row in result.all()
        }

        return {
            slot
            for slot in slots_list
            if (slot.region_id, slot.local_day, slot.local_time) in converted
        }
