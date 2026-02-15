from dataclasses import dataclass

from src.domain.enums.ad import AdType


@dataclass(frozen=True, slots=True)
class AdDTO:
    id: int
    user_id: int
    region_id: int
    ad_type: AdType
