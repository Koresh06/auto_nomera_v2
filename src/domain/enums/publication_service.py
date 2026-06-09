from enum import Enum


class PublicationServiceType(str, Enum):
    AUTOPUBLISH = "autopublish"
    PRIORITY_PUBLISH = "priority_publish"
    PIN = "pin"
    HIGHLIGHT = "highlight"
    PRE_PUBLICATION = "pre_publication"


class PublicationServiceStatus(str, Enum):
    ACTIVE = "active" # активная услуга
    USED = "used" # использована, но не оплачена
    CANCELED = "canceled" # отменена
    EXPIRED = "expired" # просрочена
