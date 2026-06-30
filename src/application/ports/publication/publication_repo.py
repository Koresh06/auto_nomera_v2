from datetime import datetime
from typing import Protocol

from src.domain.entities.publication import Publication
from src.domain.enums.ad import AdType


class PublicationRepository(Protocol):
    async def get_by_id(self, publication_id: int) -> Publication | None: ...

    async def save(self, publication: Publication) -> None: ...

    async def create(self, publication: Publication) -> Publication: ...

    async def list_scheduled_by_ad(self, ad_id: int) -> list[Publication]: ...

    async def list_by_user(
        self,
        user_id: int,
        region_id: int,
    ) -> list[tuple[Publication, str | None, str | None]]: ...

    async def count_scheduled_by_user(
        self,
        user_id: int,
        region_id: int,
        ad_type: AdType,
        from_utc: datetime,
    ) -> int: ...

    async def find_last_by_plate(
        self,
        user_id: int,
        region_id: int,
        plate: str,
        from_utc: datetime,
    ) -> Publication | None: ...

    async def list_pre_publication(
        self,
        region_id: int,
        before_utc: datetime,
    ) -> list[Publication]: ...
