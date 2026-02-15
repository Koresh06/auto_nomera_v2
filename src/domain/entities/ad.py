from dataclasses import dataclass

from src.domain.entities.base import Entity
from src.domain.enums.ad import AdType
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.store_content import StoreContent


@dataclass(kw_only=True)
class Ad(Entity):
    user_id: int
    region_id: int
    ad_type: AdType

    content: AdContent | None = None
    store_content: StoreContent | None = None

    def fill_content(self, content: AdContent) -> None:
        if self.ad_type == AdType.STORE:
            raise ValueError("STORE нельзя заполнить контентом")
        self.content = content
        self.touch()

    def fill_store_content(self, content: StoreContent) -> None:
        if self.ad_type != AdType.STORE:
            raise ValueError("AD не STORE нельзя заполнить контентом")
        self.store_content = content
        self.touch()

    def is_ready(self) -> bool:
        if self.ad_type == AdType.STORE:
            return self.store_content is not None and len(self.store_content.items) > 0
        return self.content is not None
