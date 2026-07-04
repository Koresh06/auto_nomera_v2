from datetime import datetime
from typing import Protocol

from src.application.dtos.payment_stats import PaymentStatsDTO, RegionStatDTO
from src.domain.entities.payment import Payment


class PaymentRepository(Protocol):
    async def create(self, payment: Payment) -> Payment: ...

    async def get_by_external_id(self, external_id: str) -> Payment | None: ...

    async def save(self, payment: Payment) -> None: ...

    async def get_stats(
        self,
        *,
        since_utc: datetime | None = None,
        region_id: int | None = None,
    ) -> PaymentStatsDTO: ...

    async def get_region_breakdown(
        self,
        *,
        since_utc: datetime | None = None,
    ) -> list[RegionStatDTO]: ...
