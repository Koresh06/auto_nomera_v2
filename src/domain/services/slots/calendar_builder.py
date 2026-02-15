from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.domain.entities.region import Region
from src.domain.enums.slot import SlotAvailability
from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.value_objects.calendar_slot_view import CalendarSlotView
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, slots=True)
class CalendarBuilder:
    """
    Собирает "вид" календаря для UI.
    Не ходит в Redis/DB — всё состояние передаётся параметрами.
    """

    def build(
        self,
        *,
        region: Region,
        now_utc: datetime,
        held_slots: set[SlotKey],
        booked_slots: set[SlotKey],
        converted_paid_slots: set[SlotKey],
        locale: str = "ru",
    ) -> list[CalendarSlotView]:
        if region.settings is None:
            raise ValueError("Region.settings is required to build calendar")

        settings = region.settings
        tz = ZoneInfo(region.timezone.value)  # TimezoneName VO
        now_local = now_utc.astimezone(tz)

        # 1) генерим будущие слоты (как ты делал: не показываем прошедшие)
        future_slots: list[SlotKey] = []
        day = now_local.date()

        total_needed = settings.days_range * len(settings.slot_times)

        # небольшой запас, чтобы гарантированно добрать total_needed
        for _ in range(settings.days_range + 14):
            for t in settings.slot_times:
                local_dt = datetime.combine(day, t, tzinfo=tz)
                if local_dt >= now_local:
                    future_slots.append(
                        SlotKey(
                            region_id=region.id,
                            local_day=day,
                            local_time=t,
                        )
                    )
            if len(future_slots) >= total_needed:
                break
            day = day + timedelta(days=1)

        future_slots = future_slots[:total_needed]

        # 2) pricing policy (первые N)
        policy = SlotPricingPolicy(system_paid_count=settings.system_paid_slots_count)

        # 3) собираем view
        today_local = now_local.date()
        views: list[CalendarSlotView] = []

        for slot in future_slots:
            # availability
            if slot in booked_slots:
                availability = SlotAvailability.BOOKED
            elif slot in held_slots:
                availability = SlotAvailability.HELD
            else:
                availability = SlotAvailability.FREE

            is_system_paid = policy.is_system_paid(
                ordered_future_slots=future_slots, slot=slot
            )
            is_converted_paid = slot in converted_paid_slots
            pricing = policy.resolve_pricing(
                is_system_paid=is_system_paid, is_converted_paid=is_converted_paid
            )

            # label (Сегодня/Завтра/дд.мм) — строго по локальной дате региона
            if slot.local_day == today_local:
                day_label = "Сегодня"
            elif slot.local_day == today_local + timedelta(days=1):
                day_label = "Завтра"
            else:
                day_label = f"{slot.local_day.day:02d}.{slot.local_day.month:02d}"

            prefix = "💰" if pricing.value != "free" else ""
            text = f"{prefix}{day_label}-{slot.local_time.strftime('%H:%M')}"

            views.append(
                CalendarSlotView(
                    slot_key=slot,
                    text=text,
                    availability=availability,
                    pricing=pricing,
                )
            )

        return views

    def generate_future_slots(
        self,
        *,
        region: Region,
        now_utc: datetime,
    ) -> list[SlotKey]:
        if region.settings is None:
            raise ValueError("Region.settings is required to build calendar")

        settings = region.settings
        tz = ZoneInfo(region.timezone.value)
        now_local = now_utc.astimezone(tz)

        future_slots: list[SlotKey] = []
        day = now_local.date()

        total_needed = settings.days_range * len(settings.slot_times)

        for _ in range(settings.days_range + 14):
            for t in settings.slot_times:
                local_dt = datetime.combine(day, t, tzinfo=tz)
                if local_dt >= now_local:
                    future_slots.append(
                        SlotKey(
                            region_id=region.id,
                            local_day=day,
                            local_time=t,
                        )
                    )
            if len(future_slots) >= total_needed:
                break
            day = day + timedelta(days=1)

        return future_slots[:total_needed]
