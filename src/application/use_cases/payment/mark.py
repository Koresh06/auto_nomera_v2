from dataclasses import dataclass

from src.application.exceptions.payment import PaymentNotFoundByExternalException
from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.payment import PaymentStatus
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class MarkPaymentFailedRequest(UseCaseRequest):
    external_id: str


@dataclass(kw_only=True)
class MarkPaymentFailedUseCase(UseCase[MarkPaymentFailedRequest, None]):
    payment_repo: PaymentRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: MarkPaymentFailedRequest) -> None:
        payment = await self.payment_repo.get_by_external_id(command.external_id)
        if payment is None:
            raise PaymentNotFoundByExternalException(command.external_id)
        if payment.status == PaymentStatus.PAID:
            return
        payment.mark_failed()
        await self.payment_repo.save(payment)
        await self.transaction_manager.commit()