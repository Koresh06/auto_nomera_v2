import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from src.application.exceptions.user import (
    PaymentBlockedException,
    UserNotFoundException,
)
from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.services.payment.provider_registry import PaymentProviderRegistry
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
    meta: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class CreatePaymentUseCase(UseCase[CreatePaymentRequest, Payment]):
    payment_repo: PaymentRepository
    user_repo: UserRepository
    provider_registry: PaymentProviderRegistry
    transaction_manager: TransactionManager

    async def __call__(self, command: CreatePaymentRequest) -> Payment:
        external_id = str(uuid.uuid4())
        provider = self.provider_registry.get(command.method)

        user = await self.user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        if user.is_payment_blocked:
            raise PaymentBlockedException(command.user_id)

        provider_meta = await provider.create_invoice(
            user_id=command.user_id,
            amount=command.amount,
            currency="RUB",
            description=command.description or "",
            external_id=external_id,
            phone=user.phone or "",
            chat_id=user.tg_id,
        )

        initial_status = (
            PaymentStatus.WAITING_CONFIRMATION
            if command.method == PaymentMethod.MANUAL_CARD
            else PaymentStatus.PENDING
        )

        payment = Payment(
            external_id=external_id,
            user_id=command.user_id,
            method=command.method,
            amount=command.amount,
            purpose=command.purpose,
            purpose_id=command.purpose_id,
            description=command.description,
            status=initial_status,
            meta={**command.meta, **provider_meta},
        )
        await self.payment_repo.create(payment)
        await self.transaction_manager.commit()
        return payment
