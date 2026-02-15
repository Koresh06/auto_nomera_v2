from enum import Enum


class PublicationStatus(str, Enum):
    DRAFT = "draft"          # создана, но слот не выбран/не подтвержден
    AWAITING_PAYMENT = "awaiting_payment"
    SCHEDULED = "scheduled"  # стоит в планировщике
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELED = "canceled"
    REPLACED = "replaced"    # вытеснена приоритетной публикацией (publish now)
