from dataclasses import dataclass
from datetime import datetime

from src.domain.enums.ad import AdType


@dataclass(frozen=True, slots=True)
class DeferredCardDTO:
    publication_id: int
    plate: str
    city: str
    price: int
    username: str | None
    phone: str | None
    image_file_id: str | None
    publish_at: datetime | None
    owner_tg_id: int
    ad_type: AdType

    @property
    def contacts_display(self) -> str:
        parts = []
        if self.username:
            parts.append(f"@{self.username}")
        if self.phone:
            parts.append(self.phone)
        return ", ".join(parts) or "—"

    @property
    def date_display(self) -> str:
        return self.publish_at.strftime("%d.%m.%Y, %H:%M") if self.publish_at else "—"
