from datetime import date, time

from src.domain.value_objects.slot_key import SlotKey


def encode_slot_key(slot: SlotKey) -> str:
    # region не включаем, потому что region_id обычно уже известен из контекста
    return f"{slot.local_day.isoformat()}_{slot.local_time.strftime('%H:%M')}".replace(
        "-", "_"
    ).replace(":", "_")


def decode_slot_key(region_id: int, raw: str) -> SlotKey:
    # raw: YYYY_MM_DD_HH_MM
    parts = raw.split("_")
    if len(parts) != 5:
        raise ValueError("Invalid slot key format")

    yyyy, mm, dd, hh, minute = map(int, parts)
    return SlotKey(
        region_id=region_id,
        local_day=date(yyyy, mm, dd),
        local_time=time(hh, minute),
    )
