from dataclasses import dataclass

from src.domain.entities.ad import Ad
from src.domain.enums.ad import AdStatus, AdType
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.store_content import StoreContent


@dataclass(frozen=True)
class AdDTO:
    id: int
    user_id: int
    region_id: int
    ad_type: AdType
    status: AdStatus

    content: AdContent | None = None
    store_content: StoreContent | None = None

    @classmethod
    def from_entity(cls, entity: Ad) -> "AdDTO":
        return cls(
            id=entity.id,
            user_id=entity.user_id,
            region_id=entity.region_id,
            ad_type=entity.ad_type,
            status=entity.status,
            content=entity.content,
            store_content=entity.store_content,
        )
    
    