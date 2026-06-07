from enum import Enum


class AdStatus(str, Enum):
    DRAFT = "draft"  # создаётся в боте
    READY = "ready"  # заполнено, можно выбирать слот/оплачивать
    SCHEDULED = "scheduled"  # есть план публикаций
    PUBLISHED = "published"  # опубликована хотя бы раз
    ARCHIVED = "archived"  # снята/устарела


class AdType(str, Enum):
    SALE = "sale"
    BUY = "buy"
    URGENT_BUYOUT = "urgent_buyout"
    STORE = "store"

    @property
    def display(self) -> str:
        labels = {
            "sale": "📌 ПРОДАМ НОМЕРА",
            "buy": "📌 КУПЛЮ НОМЕРА",
            "urgent_buyout": "📌 СРОЧНЫЙ ВЫКУП",
            "store": "📌 МАГАЗИН",
        }
        return labels.get(self.value, "📌 ОБЪЯВЛЕНИЕ")