import uuid
from dataclasses import dataclass
from decimal import Decimal

from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.payment import Payment
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class CreatePaymentRequest(UseCaseRequest):
    user_id: int
    amount: Decimal
    method: PaymentMethod
    purpose: PaymentPurpose
    purpose_id: int | None = None
    description: str | None = None
    external_id: str | None = None  # если уже есть от платёжки


@dataclass(kw_only=True)
class CreatePaymentUseCase(UseCase[CreatePaymentRequest, Payment]):
    payment_repo: PaymentRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: CreatePaymentRequest) -> Payment:
        payment = Payment(
            external_id=command.external_id or str(uuid.uuid4()),
            user_id=command.user_id,
            method=command.method,
            amount=command.amount,
            purpose=command.purpose,
            purpose_id=command.purpose_id,
            description=command.description,
            status=PaymentStatus.PENDING,
        )
        await self.payment_repo.create(payment)
        await self.transaction_manager.commit()
        return payment