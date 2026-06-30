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
from src.application.services.notification.notification_service import NotificationService
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
    notification_service: NotificationService
    transaction_manager: TransactionManager

    async def __call__(self, command: ConfirmPaymentRequest) -> None:
        logger.info(f"[ConfirmPayment:start] external_id={command.external_id}")
        now = command.now_utc or datetime.now(timezone.utc)

        payment = await self.payment_repo.get_by_external_id(command.external_id)
        if payment is None:
            logger.warning(f"[ConfirmPayment:not_found] external_id={command.external_id}")
            raise PaymentNotFoundByExternalException(command.external_id)

        logger.info(
            f"[ConfirmPayment:loaded] payment_id={payment.id} status={payment.status} "
            f"purpose={payment.purpose} meta={payment.meta}"
        )

        if payment.status == PaymentStatus.PAID:
            logger.info(f"[ConfirmPayment:already_paid] external_id={command.external_id}")
            return

        payment.mark_paid(now)
        await self.payment_repo.save(payment)
        logger.info(f"[ConfirmPayment:marked_paid] payment_id={payment.id}")

        user = await self.user_repo.get_by_id(payment.user_id)
        if user is None:
            raise UserNotFoundException(payment.user_id)

        extra: dict = {}

        if payment.purpose == PaymentPurpose.BALANCE_TOPUP:
            logger.info("[ConfirmPayment:branch] BALANCE_TOPUP")
            user.top_up(payment.amount)
            await self.user_repo.save(user)

        elif payment.purpose == PaymentPurpose.PUBLICATION_SERVICE:
            logger.info("[ConfirmPayment:branch] PUBLICATION_SERVICE")
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
            await self.transaction_manager.commit()
            logger.info(f"[ConfirmPayment:service_applied] pub_id={publication.id} type={definition.type}")

            if definition.type == PublicationServiceType.PRIORITY_PUBLISH:
                await self.priority_publish(
                    PriorityPublishPublicationRequest(publication_id=publication.id)
                )
                logger.info(f"[ConfirmPayment:priority_published] pub_id={publication.id}")
            elif publication.status == PublicationStatus.PUBLISHED:
                await self.apply_service_to_published(
                    ApplyServiceToPublishedRequest(
                        publication_id=publication.id,
                        service_type=definition.type,
                    )
                )

            logger.info(f"[ConfirmPayment:before_notify] payment_id={payment.id}")
            await self._notify_success(payment, extra={"title": definition.title})
            logger.info(f"[ConfirmPayment:before_teleport] payment_id={payment.id} meta={payment.meta}")
            await self._teleport_back(payment)
            logger.info(f"[ConfirmPayment:after_teleport] payment_id={payment.id}")
            return

        elif payment.purpose == PaymentPurpose.PRE_PUBLICATION:
            logger.info("[ConfirmPayment:branch] PRE_PUBLICATION")
            days = payment.meta.get("days", 30)
            was_active = user.has_pre_publication
            user.activate_pre_publication(days)
            await self.user_repo.save(user)
            extra["days"] = days
            extra["was_active"] = was_active

        elif payment.purpose == PaymentPurpose.SLOT:
            logger.info("[ConfirmPayment:branch] SLOT")
            return_data = payment.meta.get("return_data", {})

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
                extra["slot_text"] = f"{publication.publish_at_utc:%d.%m}-{publication.publish_at_utc:%H:%M}"
            elif "slot" in return_data:
                slot_dict = return_data["slot"]
                slot = SlotKey(
                    region_id=slot_dict["region_id"],
                    local_day=date.fromisoformat(slot_dict["slot_day"]),
                    local_time=time.fromisoformat(slot_dict["slot_time"]),
                )
                await self.reservation_service.converted_repo.mark_converted(
                    slot=slot,
                    user_id=payment.user_id,
                    ad_id=None,
                )
                extra["slot_text"] = f"{slot.local_day:%d.%m} {slot.local_time:%H:%M}"
                logger.info(
                    f"[ConfirmPayment:slot_converted] user_id={payment.user_id} "
                    f"slot={slot.local_day} {slot.local_time}"
                )
            else:
                raise PaymnetNotFountPurposeException(command.external_id)

        await self.transaction_manager.commit()

        logger.info(f"[ConfirmPayment:before_notify] payment_id={payment.id} extra={extra}")
        await self._notify_success(payment, extra=extra)
        logger.info(f"[ConfirmPayment:before_teleport] payment_id={payment.id} meta={payment.meta}")
        await self._teleport_back(payment)
        logger.info(f"[ConfirmPayment:after_teleport] payment_id={payment.id}")

        logger.info(
            f"[ConfirmPayment:done] external_id={command.external_id} purpose={payment.purpose}"
        )

    async def _notify_success(self, payment: Payment, extra: dict | None = None) -> None:
        return_to = payment.meta.get("return_to")
        if not return_to:
            logger.warning(f"[ConfirmPayment:notify_skip] no return_to, payment_id={payment.id}")
            return
        text = self._build_success_text(payment, extra)
        try:
            await self.notification_service.notify_user(
                tg_id=return_to["user_id"],
                text=text,
            )
            logger.info(f"[ConfirmPayment:notify_sent] tg_id={return_to['user_id']}")
        except Exception as e:
            logger.warning(f"[ConfirmPayment:notify_failed] {e}")

    async def _teleport_back(self, payment: Payment) -> None:
        return_to = payment.meta.get("return_to")
        return_state = payment.meta.get("return_state")
        return_data = payment.meta.get("return_data", {})

        logger.info(
            f"[ConfirmPayment:teleport_check] return_to={return_to} "
            f"return_state={return_state!r} return_data={return_data}"
        )

        if not return_to or not return_state:
            logger.warning(
                f"[ConfirmPayment:teleport_skip] return_to_empty={not return_to} "
                f"return_state_empty={not return_state}"
            )
            return

        try:
            await self.teleporter.start(
                user_id=return_to["user_id"],
                chat_id=return_to["chat_id"],
                state_key=return_state,
                data=return_data,
            )
            logger.info(f"[ConfirmPayment:teleport_success] state_key={return_state}")
        except Exception as e:
            logger.warning(f"[ConfirmPayment:teleport_failed] {e}")


    @staticmethod
    def _build_success_text(payment: Payment, extra: dict | None = None) -> str:
        extra = extra or {}
        header = "🎉 <b>Оплата прошла успешно!</b>"
    
        match payment.purpose:
            case PaymentPurpose.BALANCE_TOPUP:
                body = f"✨ Баланс пополнен на <b>{payment.amount} ₽</b>"
    
            case PaymentPurpose.PUBLICATION_SERVICE:
                title = extra.get("title", "Услуга")
                body = f"<b>{title}</b>\nУслуга подключена и применена к объявлению"
    
            case PaymentPurpose.PRE_PUBLICATION:
                days = extra.get("days", 30)
                action = "продлена" if extra.get("was_active") else "активирована"
                body = f"💎 Подписка на ранний доступ <b>{action}</b>\nна {days} дн."
    
            case PaymentPurpose.SLOT:
                slot_text = extra.get("slot_text", "")
                suffix = f"\n🕒 {slot_text}" if slot_text else ""
                body = f"📅 Слот <b>оплачен и забронирован</b>!{suffix}"
    
            case _:
                body = "✅ Платёж подтверждён"
    
        return f"{header}\n\n{body}"
