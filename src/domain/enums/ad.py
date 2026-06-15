from enum import Enum


class AdStatus(str, Enum):
    DRAFT = "draft"                         # создаётся в боте, поля не заполнены
    PENDING_MODERATION = "pending_moderation"  # URGENT_BUYOUT — ждёт одобрения админа
    READY = "ready"                         # заполнено, можно выбирать слот / оплачивать
    SCHEDULED = "scheduled"                 # запланирована хотя бы одна публикация
    PUBLISHED = "published"                 # опубликована хотя бы раз в канале; для URGENT_BUYOUT — одобрена админом и доступна юзерам с pre_publication
    ARCHIVED = "archived"                   # снята, устарела или отклонена админом (URGENT_BUYOUT)


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