from dataclasses import dataclass

from src.domain.entities.publication import PublicationStatus
from src.domain.entities.ad import AdType


_STATUS_LABELS = {
    PublicationStatus.SCHEDULED: "🕒 Запланировано",
    PublicationStatus.PUBLISHING: "📤 Публикуется",
    PublicationStatus.PUBLISHED: "✅ Опубликовано",
    PublicationStatus.FAILED: "❌ Ошибка",
    PublicationStatus.CANCELED: "🚫 Отменено",
    PublicationStatus.REPLACED: "♻️ Вытеснено",
    PublicationStatus.DRAFT: "📝 Черновик",
    PublicationStatus.AWAITING_PAYMENT: "💳 Ждёт оплаты",
}

_AD_TYPE_LABELS = {
    AdType.SALE: "📤 Продажа",
    AdType.BUY: "📥 Покупка",
    AdType.URGENT_BUYOUT: "⚠️ Срочный выкуп",
    AdType.STORE: "🏦 Магазин",
}


@dataclass(frozen=True, slots=True)
class StatusStatDTO:
    status: PublicationStatus
    count: int

    @property
    def label(self) -> str:
        return _STATUS_LABELS.get(self.status, self.status.value)


@dataclass(frozen=True, slots=True)
class AdTypeStatDTO:
    ad_type: AdType
    count: int

    @property
    def label(self) -> str:
        return _AD_TYPE_LABELS.get(self.ad_type, self.ad_type.value)


@dataclass(frozen=True, slots=True)
class PublicationStatsDTO:
    total: int
    by_status: list[StatusStatDTO]
    by_ad_type: list[AdTypeStatDTO]
    top_region_title: str | None
    top_region_count: int
