import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from src.application.exceptions.payment import (
    PaymentNotFoundByExternalException,
    PaymnetNotFountPurposeException,
)
from src.application.exceptions.publication import PublicationNotFoundException
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.dialog.teleport import DialogTeleporter
from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication_service.service_definition_repo import (
    ServiceDefinitionRepository,
)
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.use_cases.publication.confirm_paid_slot_and_schedule_publication import (
    ConfirmPaidSlotAndSchedulePublicationRequest,
    ConfirmPaidSlotAndSchedulePublicationUseCase,
)
from src.application.use_cases.publication_service.apply_service import ApplyServiceToPublishedRequest, ApplyServiceToPublishedUseCase
from src.application.use_cases.publication_service.priority_publish_publication import PriorityPublishPublicationRequest, PriorityPublishPublicationUseCase
from src.domain.entities.payment import Payment, PaymentStatus
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.payment import PaymentPurpose
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.value_objects.slot_key import SlotKey
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
    confirm_paid_slot: ConfirmPaidSlotAndSchedulePublicationUseCase
    apply_service_to_published: ApplyServiceToPublishedUseCase
    priority_publish: PriorityPublishPublicationUseCase
    reservation_service: SlotReservationService
    teleporter: DialogTeleporter
    transaction_manager: TransactionManager

    async def __call__(self, command: ConfirmPaymentRequest) -> None:
        now = command.now_utc or datetime.now(timezone.utc)

        payment = await self.payment_repo.get_by_external_id(command.external_id)
        if payment is None:
            raise PaymentNotFoundByExternalException(command.external_id)

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
            definition = await self.service_def_repo.get_by_type(
                PublicationServiceType(payment.meta["service_type"])
            )
            if not payment.purpose_id:
                raise PaymnetNotFountPurposeException(command.external_id)

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
            await self.transaction_manager.commit()  # фиксируем покупку

            # применяем сразу
            if definition.type == PublicationServiceType.PRIORITY_PUBLISH:
                await self.priority_publish(
                    PriorityPublishPublicationRequest(publication_id=publication.id)
                )
            elif publication.status == PublicationStatus.PUBLISHED:
                await self.apply_service_to_published(
                    ApplyServiceToPublishedRequest(
                        publication_id=publication.id,
                        service_type=definition.type,
                    )
                )

            await self._teleport_back(payment)
            return  # коммит уже сделан выше

        elif payment.purpose == PaymentPurpose.PRE_PUBLICATION:
            days = payment.meta.get("days", 30)
            user.activate_pre_publication(days)
            await self.user_repo.save(user)

        elif payment.purpose == PaymentPurpose.SLOT:
            return_data = payment.meta.get("return_data", {})
            logger.info(f"[ConfirmPayment:SLOT debug] meta={payment.meta} return_data={return_data}")

            if payment.purpose_id:
                publication = await self.publication_repo.get_by_id(payment.purpose_id)
                if publication is None:
                    raise PublicationNotFoundException(payment.purpose_id)

                await self.confirm_paid_slot(
                    ConfirmPaidSlotAndSchedulePublicationRequest(
                        publication_id=publication.id,
                        user_id=payment.user_id,
                        ad_id=publication.ad_id,
                    )
                )
            elif "slot" in return_data:
                slot_dict = return_data["slot"]
                slot = SlotKey(
                    region_id=slot_dict["region_id"],
                    local_day=date.fromisoformat(slot_dict["local_day"]),
                    local_time=time.fromisoformat(slot_dict["local_time"]),
                )
                await self.reservation_service.converted_repo.mark_converted(
                    slot=slot,
                    user_id=payment.user_id,
                    ad_id=None,
                )
                logger.info(
                    f"[ConfirmPayment:slot_converted] user_id={payment.user_id} "
                    f"slot={slot.local_day} {slot.local_time}"
                )
            else:
                raise PaymnetNotFountPurposeException(command.external_id)

        await self.transaction_manager.commit()

        await self._teleport_back(payment)

        logger.info(
            f"[ConfirmPayment:done] external_id={command.external_id} purpose={payment.purpose}"
        )

    async def _teleport_back(self, payment: Payment) -> None:
        return_to = payment.meta.get("return_to")
        return_state = payment.meta.get("return_state")
        return_data = payment.meta.get("return_data", {})

        if not return_to:
            return

        try:
            await self.teleporter.done(
                user_id=return_to["user_id"],
                chat_id=return_to["chat_id"],
            )
            if return_state:
                await self.teleporter.update(
                    user_id=return_to["user_id"],
                    chat_id=return_to["chat_id"],
                    data=return_data,
                )
                await self.teleporter.switch_to(
                    user_id=return_to["user_id"],
                    chat_id=return_to["chat_id"],
                    state_key=return_state,
                )
        except Exception as e:
            logger.warning(f"[ConfirmPayment:teleport_failed] {e}")