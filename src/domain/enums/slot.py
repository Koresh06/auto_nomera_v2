from enum import Enum


class SlotAvailability(str, Enum):
    FREE = "free"
    HELD = "held"
    BOOKED = "booked"


class SlotPricing(str, Enum):
    FREE = "free"
    SYSTEM = "system"  # первые N слотов по политике региона
    CONVERTED = "converted"  # стал платным, потому что пользователь выбрал бесплатный
