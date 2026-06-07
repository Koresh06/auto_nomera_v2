from typing import Protocol

from src.domain.entities.publication import Publication


class PublicationRepository(Protocol):
    async def get_by_id(self, publication_id: int) -> Publication | None: ...

    async def save(self, publication: Publication) -> None: ...

    async def create(self, publication: Publication) -> Publication: ...

    async def list_scheduled_by_ad(self, ad_id: int) -> list[Publication]: ...

    async def list_by_user(
        self,
        user_id: int,
        region_id: int,
    ) -> list[tuple[Publication, str | None]]: ...
