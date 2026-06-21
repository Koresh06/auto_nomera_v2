from typing import Protocol

from src.domain.entities.payment import Payment


class PaymentRepository(Protocol):
    async def create(self, payment: Payment) -> Payment: ...

    async def get_by_external_id(self, external_id: str) -> Payment | None: ...
    
    async def save(self, payment: Payment) -> None: ...