from __future__ import annotations

from dataclasses import replace
from typing import Dict

from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.region.region_repo import RegionRepository

from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region


class _AutoId:
    def __init__(self) -> None:
        self._n = 1

    def next(self) -> int:
        n = self._n
        self._n += 1
        return n


class InMemoryAdRepo(AdRepository):
    def __init__(self) -> None:
        self._ids = _AutoId()
        self._items: Dict[int, Ad] = {}

    async def get_by_id(self, ad_id: int) -> Ad:
        return self._items[ad_id]

    async def create(self, ad: Ad) -> None:
        ad.id = self._ids.next()
        self._items[ad.id] = ad

    async def save(self, ad: Ad) -> None:
        self._items[ad.id] = ad


class InMemoryPublicationRepo(PublicationRepository):
    def __init__(self) -> None:
        self._ids = _AutoId()
        self._items: Dict[int, Publication] = {}

    async def get_by_id(self, publication_id: int) -> Publication:
        return self._items[publication_id]

    async def create(self, publication: Publication) -> None:
        publication.id = self._ids.next()
        self._items[publication.id] = publication

    async def save(self, publication: Publication) -> None:
        self._items[publication.id] = publication


class InMemoryRegionRepo(RegionRepository):
    def __init__(self, regions: list[Region]) -> None:
        self._items = {r.id: r for r in regions}

    async def get_by_id(self, region_id: int) -> Region:
        return self._items[region_id]
