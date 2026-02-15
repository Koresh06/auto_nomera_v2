from dataclasses import dataclass
from datetime import date, time

from src.domain.enums.publication import PublicationPlanMode
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, slots=True)
class PublicationPlan:
    mode: PublicationPlanMode

    # SINGLE
    slot: SlotKey | None = None

    # AUTODAILY
    days_total: int = 0
    time_local: time | None = None
    start_date_local: date | None = None
