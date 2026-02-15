from typing import Protocol

from src.domain.entities.publication import Publication


class PublicationRepository(Protocol):
    async def get_by_id(self, publication_id: int) -> Publication:
        ...

    async def save(self, publication: Publication) -> None:
        ...

    async def create(self, publication: Publication) -> None:
       ...