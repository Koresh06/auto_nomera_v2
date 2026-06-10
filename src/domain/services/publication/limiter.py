from dataclasses import dataclass
from datetime import timedelta

from src.domain.enums.ad import AdType


@dataclass(frozen=True, slots=True)
class LimitCheckResult:
    allowed: bool
    reason: str | None = None

    @classmethod
    def ok(cls) -> "LimitCheckResult":
        return cls(allowed=True)

    @classmethod
    def denied(cls, reason: str) -> "LimitCheckResult":
        return cls(allowed=False, reason=reason)


FREE_LIMITS = {
    AdType.SALE: 5,
    AdType.BUY: 5,
    AdType.STORE: 2,
    AdType.URGENT_BUYOUT: 5,
}

INTERVAL = timedelta(days=7)