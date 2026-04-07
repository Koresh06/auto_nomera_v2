from dataclasses import dataclass

from src.domain.entities.base import Entity
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)


@dataclass(kw_only=True)
class PublicationService(Entity):
    type: PublicationServiceType
    status: PublicationServiceStatus = PublicationServiceStatus.ACTIVE
    params: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.params is None:
            self.params = {}

    def mark_used(self) -> None:
        self.status = PublicationServiceStatus.USED
        self.touch()

    def cancel(self) -> None:
        self.status = PublicationServiceStatus.CANCELED
        self.touch()
