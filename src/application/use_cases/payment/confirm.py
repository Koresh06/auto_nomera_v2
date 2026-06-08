import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.exceptions.payment import PaymentNotFoundException
from src.application.exceptions.publication import PublicationNotFoundException
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication_service.service_definition_repo import ServiceDefinitionRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.payment import PaymentStatus
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.payment import PaymentPurpose
from src.domain.enums.publication_service import PublicationServiceType
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ConfirmPaymentRequest(UseCaseRequest):
    external_id: str
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class ConfirmPaymentUseCase(UseCase[ConfirmPaymentRequest, None]):
    payment_repo: PaymentRepository
    user_repo: UserRepository
    publication_repo: PublicationRepository
    service_def_repo: ServiceDefinitionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: ConfirmPaymentRequest) -> None:
        now = command.now_utc or datetime.now(timezone.utc)

        payment = await self.payment_repo.get_by_external_id(command.external_id)
        if payment is None:
            raise PaymentNotFoundException(command.external_id)

        if payment.status == PaymentStatus.PAID:
            return  # идемпотентность — уже обработан

        payment.mark_paid(now)
        await self.payment_repo.save(payment)

        user = await self.user_repo.get_by_id(payment.user_id)
        if user is None:
            raise UserNotFoundException(payment.user_id)

        # применяем в зависимости от цели платежа
        if payment.purpose == PaymentPurpose.BALANCE_TOPUP:
            user.top_up(payment.amount)
            await self.user_repo.save(user)

        elif payment.purpose == PaymentPurpose.PUBLICATION_SERVICE:
            # покупаем услугу к публикации
            definition = await self.service_def_repo.get_by_type(
                PublicationServiceType(payment.meta["service_type"])
            )
            publication = await self.publication_repo.get_by_id(payment.purpose_id)
            if publication is None:
                raise PublicationNotFoundException(payment.purpose_id)
            service = PublicationService(
                type=definition.type,
                price_paid=definition.price,
                params=payment.meta.get("params", {}),
            )
            publication.add_service(service)
            await self.publication_repo.save(publication)

        elif payment.purpose == PaymentPurpose.PRE_PUBLICATION:
            months = payment.meta.get("months", 1)
            user.activate_pre_publication(months=months)
            await self.user_repo.save(user)

        elif payment.purpose == PaymentPurpose.SLOT:
            # подтверждение оплаты слота — отдельный use case
            pass  # TODO: ConfirmPaidSlotAndSchedulePublication

        await self.transaction_manager.commit()
        logger.info(f"[ConfirmPayment:done] external_id={command.external_id} purpose={payment.purpose}")