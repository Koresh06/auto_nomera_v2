from dataclasses import dataclass

from src.domain.enums.ad import AdType
from src.domain.enums.publication import PublicationStatus

@dataclass(frozen=True, slots=True)
class ScheduleSlotDTO:
    publication_id: int
    time: str
    plate: str
    ad_type: AdType
    status: PublicationStatus
    owner_tg_id: int
    owner_username: str | None

    @property
    def type_emoji(self) -> str:
        return {
            AdType.SALE: "🔴",
            AdType.BUY: "🟢",
            AdType.URGENT_BUYOUT: "⚡",
            AdType.STORE: "🏪",
        }.get(self.ad_type, "▫️")

    @property
    def status_emoji(self) -> str:
        return {
            PublicationStatus.PUBLISHED: "✅",
            PublicationStatus.SCHEDULED: "🕓",
            PublicationStatus.PUBLISHING: "📤",
        }.get(self.status, "▫️")
    
    @property
    def owner_link(self) -> str:
        if self.owner_username:
            return f'<a href="https://t.me/{self.owner_username}">👤</a>'
        return f'<a href="tg://user?id={self.owner_tg_id}">👤</a>'


@dataclass(frozen=True, slots=True)
class ScheduleDayDTO:
    date: str
    slots: list[ScheduleSlotDTO]

    @property
    def count(self) -> int:
        return len(self.slots)


@dataclass(frozen=True, slots=True)
class RegionScheduleDTO:
    region_title: str
    days: list[ScheduleDayDTO]