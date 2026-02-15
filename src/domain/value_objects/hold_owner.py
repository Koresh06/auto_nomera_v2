from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HoldOwner:
    user_id: int
    ad_id: int