from dataclasses import dataclass

from src.application.exceptions.payment import PaymentNotFoundByExternalException
from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.payment import Payment


@dataclass(frozen=True, eq=False)
class GetPaymentByExternalIdRequest(UseCaseRequest):
    external_id: str


@dataclass(kw_only=True)
class GetPaymentByExternalIdUseCase(UseCase[GetPaymentByExternalIdRequest, Payment]):
    payment_repo: PaymentRepository

    async def __call__(self, command: GetPaymentByExternalIdRequest) -> Payment:
        payment = await self.payment_repo.get_by_external_id(command.external_id)
        if payment is None:
            raise PaymentNotFoundByExternalException(command.external_id)
        return payment
