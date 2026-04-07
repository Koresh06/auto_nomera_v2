from enum import Enum


class PublicationServiceType(str, Enum):
    AUTOPUBLISH = "autopublish"  # N дней подряд в то же время
    PRIORITY_PUBLISH = "priority_publish"  # опубликовать прямо сейчас
    PIN = "pin"  # закрепить
    HIGHLIGHT = "highlight"  # рамка (красная)


class PublicationServiceStatus(str, Enum):
    ACTIVE = "active"
    USED = "used"
    CANCELED = "canceled"
    EXPIRED = "expired"
