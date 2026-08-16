from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


@dataclass(frozen=True, slots=True)
class PaymentDetailItemDTO:
    tg_id: int
    full_name: str | None
    username: str | None
    amount: Decimal
    method_value: str
    paid_at: datetime | None

    @property
    def owner_link(self) -> str:
        name = self.full_name or self.username or "Без имени"
        return f'<a href="tg://user?id={self.tg_id}">{name} - [профиль]</a>'

    @property
    def paid_at_msk_display(self) -> str:
        if self.paid_at is None:
            return "—"
        local_dt = self.paid_at.astimezone(MOSCOW_TZ)
        return local_dt.strftime("%d.%m.%Y %H:%M:%S")

    @property
    def card_text(self) -> str:
        return (
            f"👤 {self.owner_link}\n"
            f"🆔 TG ID: <code>{self.tg_id}</code>\n"
            f"💰 {self.amount:.0f} руб. | 💳 {self.method_value.lower()}\n"
            f"🕓 {self.paid_at_msk_display} (МСК)"
        )
