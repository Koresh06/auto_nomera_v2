from src.application.ports.publication.publication_repo import PublicationRepository
from src.domain.entities.publication import Publication
from src.domain.enums.publication import PublicationStatus
from src.infrastructure.repositories.utils import _AutoId


class InMemoryPublicationRepo(PublicationRepository):
    def __init__(self) -> None:
        self._ids = _AutoId()
        self._items: dict[int, Publication] = {}

    async def get_by_id(self, publication_id: int) -> Publication:
        return self._items[publication_id]

    async def create(self, publication: Publication) -> None:
        publication.id = self._ids.next()
        self._items[publication.id] = publication

    async def save(self, publication: Publication) -> None:
        self._items[publication.id] = publication

    async def list_scheduled_by_ad(self, ad_id: int) -> list[Publication]:
        return [
            p
            for p in self._items.values()
            if p.ad_id == ad_id and p.status == PublicationStatus.SCHEDULED
        ]