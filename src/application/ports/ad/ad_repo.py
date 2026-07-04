from typing import Protocol
from src.domain.entities.ad import Ad
from src.domain.enums.ad import AdType


class AdRepository(Protocol):
    async def get_by_id(self, ad_id: int) -> Ad | None: ...

    async def create(self, ad: Ad) -> Ad: ...

    async def save(self, ad: Ad) -> None: ...

    async def find_by_plate(
        self,
        user_id: int,
        region_id: int,
        plate_number: str,
    ) -> Ad | None: ...

    async def find_store_by_user(
        self,
        user_id: int,
        region_id: int,
    ) -> Ad | None: ...

    async def list_urgent_published(self, region_id: int) -> list[Ad]: ...

    async def count_ads_by_user(
        self,
        user_id: int,
        region_id: int,
    ) -> int: ...

    async def count_ads(self, since_utc=None, region_id=None) -> int: ...

    async def count_by_type(
        self, since_utc=None, region_id=None
    ) -> list[tuple[AdType, int]]: ...
