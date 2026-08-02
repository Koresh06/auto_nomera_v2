from dataclasses import dataclass

from src.application.dtos.payment import PaymentDetailItemDTO
from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.period import StatsPeriod


@dataclass(frozen=True, eq=False)
class GetPaymentDetailsRequest(UseCaseRequest):
    period: StatsPeriod
    region_id: int | None = None


@dataclass(kw_only=True)
class GetPaymentDetailsUseCase(
    UseCase[GetPaymentDetailsRequest, list[PaymentDetailItemDTO]]
):
    payment_repo: PaymentRepository

    async def __call__(
        self, command: GetPaymentDetailsRequest
    ) -> list[PaymentDetailItemDTO]:
        since = command.period.since_utc()
        rows = await self.payment_repo.list_paid_payments(
            since_utc=since, region_id=command.region_id
        )
        return [
            PaymentDetailItemDTO(
                tg_id=tg_id,
                full_name=full_name,
                username=username,
                amount=payment.amount,
                method_value=payment.method.value,
                paid_at=payment.paid_at,
            )
            for payment, tg_id, full_name, username in rows
        ]
