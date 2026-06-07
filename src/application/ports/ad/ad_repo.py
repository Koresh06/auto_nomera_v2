from typing import Protocol
from src.domain.entities.ad import Ad


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
