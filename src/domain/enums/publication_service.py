from enum import Enum


class PublicationServiceType(str, Enum):
    AUTOPUBLISH = "autopublish"
    PRIORITY_PUBLISH = "priority_publish"
    PIN = "pin"
    HIGHLIGHT = "highlight"
    PRE_PUBLICATION = "pre_publication"

    @property
    def display(self) -> str:
        return {
            PublicationServiceType.AUTOPUBLISH: "🔂 Автопубликация",
            PublicationServiceType.PRIORITY_PUBLISH: "🥇 Вне очереди",
            PublicationServiceType.PIN: "📌 Закрепление",
            PublicationServiceType.HIGHLIGHT: "🟥 Выделение",
            PublicationServiceType.PRE_PUBLICATION: "💎 Объявления до публикации",
        }[self]


class PublicationServiceStatus(str, Enum):
    ACTIVE = "active"  # активная услуга
    USED = "used"  # использована
    CANCELED = "canceled"  # отменена
    EXPIRED = "expired"  # просрочена
