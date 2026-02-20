from src.application.ports.ad.ad_repo import AdRepository
from src.domain.entities.ad import Ad
from src.infrastructure.repositories.utils import _AutoId



class InMemoryAdRepo(AdRepository):
    def __init__(self) -> None:
        self._ids = _AutoId()
        self._items: dict[int, Ad] = {}

    async def get_by_id(self, ad_id: int) -> Ad:
        return self._items[ad_id]

    async def create(self, ad: Ad) -> None:
        ad.id = self._ids.next()
        self._items[ad.id] = ad

    async def save(self, ad: Ad) -> None:
        self._items[ad.id] = ad