from enum import Enum


class PublicationServiceType(str, Enum):
    AUTOPUBLISH = "autopublish"
    PRIORITY_PUBLISH = "priority_publish"
    PIN = "pin"
    HIGHLIGHT = "highlight"


class PublicationServiceStatus(str, Enum):
    ACTIVE = "active"
    USED = "used"
    CANCELED = "canceled"
    EXPIRED = "expired"
