from datetime import datetime, time, timezone, date

from src.domain.entities.region import Region
from src.domain.value_objects.timezone_name import TimezoneName
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.services.calendar_builder import CalendarBuilder
from src.domain.value_objects.slot_key import SlotKey


def main():
    region = Region(
        id=20,
        title="Минск",
        timezone=TimezoneName("Europe/Minsk"),
        channel_id=-1001234567890,
        settings=RegionSettings(
            slot_times=(time(10, 0), time(14, 0), time(18, 0)),
            days_range=7,
            system_paid_slots_count=3,
        ),
    )

    now_utc = datetime.now(timezone.utc)

    held = {
        SlotKey(
            region_id=20,
            local_day=date(2026, 2, 12),
            local_time=time(14, 0),
        ),
    }
    booked = {
        SlotKey(
            region_id=20,
            local_day=date(2026, 2, 12),
            local_time=time(18, 0),
        )
    }
    converted = {
        SlotKey(
            region_id=20,
            local_day=date(2026, 2, 13),
            local_time=time(10, 0),
        )
    }

    slots = CalendarBuilder().build(
        region=region,
        now_utc=now_utc,
        held_slots=held,
        booked_slots=booked,
        converted_paid_slots=converted,
    )

    for s in slots:
        print(
            f"{s.text:15} | disabled={s.is_disabled} | availability={s.availability.value:6} | pricing={s.pricing.value}"
        )


if __name__ == "__main__":
    main()
