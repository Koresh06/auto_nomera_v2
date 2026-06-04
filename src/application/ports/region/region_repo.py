from typing import Protocol

from src.domain.entities.region import Region


class RegionRepository(Protocol):
    async def get_by_id(self, region_id: int) -> Region | None: ...

    async def get_all(self) -> list[Region]: ...

    async def create(self, region: Region) -> Region: ...
