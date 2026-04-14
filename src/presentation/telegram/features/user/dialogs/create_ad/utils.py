from datetime import date, time


def _decode_slot_id(slot_id: str) -> tuple[date, time]:
    # ожидаем формат: YYYY_MM_DD_HH_MM
    y, m, d, hh, mm = map(int, slot_id.split("_"))
    return date(y, m, d), time(hh, mm)