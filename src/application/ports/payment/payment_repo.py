from datetime import datetime
from typing import Protocol

from src.application.dtos.payment_stats import PaymentStatsDTO, RegionStatDTO
from src.domain.entities.payment import Payment


class PaymentRepository(Protocol):
    async def create(self, payment: Payment) -> Payment: ...

    async def get_by_external_id(self, external_id: str) -> Payment | None: ...

    async def get_by_external_id_for_update(self, external_id: str) -> Payment | None:
        """Как get_by_external_id, но блокирует строку (SELECT ... FOR UPDATE)
        до конца транзакции — используется только там, где платёж подтверждается,
        чтобы два параллельных подтверждения одного external_id не выполнились
        одновременно (повтор webhook'а, повторная доставка задачи)."""
        ...

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

    async def list_paid_payments(
        self,
        *,
        since_utc: datetime | None = None,
        region_id: int | None = None,
    ) -> list[tuple[Payment, int, str | None, str | None]]: ...
