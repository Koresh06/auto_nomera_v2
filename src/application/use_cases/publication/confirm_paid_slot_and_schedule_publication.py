from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.publication import PublicationStatus
from src.domain.exceptions.publication import InvalidPublicationState
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class ConfirmPaidSlotAndSchedulePublicationRequest(UseCaseRequest):
    publication_id: int
    user_id: int
    ad_id: int
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class ConfirmPaidSlotAndSchedulePublicationUseCase(
    UseCase[ConfirmPaidSlotAndSchedulePublicationRequest, None]
):
    publication_repo: PublicationRepository
    scheduler: Scheduler
    reservation_service: SlotReservationService
    transaction_manager: TransactionManager

    async def __call__(
        self, command: ConfirmPaidSlotAndSchedulePublicationRequest
    ) -> None:
        publication = await self.publication_repo.get_by_id(command.publication_id)
        if publication is None:
            raise PublicationNotFoundException(command.publication_id)

        # 1) Проверяем, что публикация ожидает оплату (или хотя бы ещё не scheduled)
        if publication.status not in (
            PublicationStatus.AWAITING_PAYMENT,
            PublicationStatus.DRAFT,
        ):
            raise InvalidPublicationState(
                f"Publication must be awaiting payment or draft, got {publication.status}"
            )

        if publication.slot is None or publication.publish_at_utc is None:
            raise ValueError(
                "Publication slot/publish_at_utc must be set before confirming payment"
            )

        # 2) Фиксируем booking слота (занят окончательно)
        await self.reservation_service.book_after_payment(
            slot=publication.slot,
            user_id=command.user_id,
            ad_id=command.ad_id,
            require_hold_owner=False,  # TTL мог истечь — но если слот ещё свободен, мы забронируем
        )

        # 3) Переводим публикацию в scheduled и ставим задачу
        publication.schedule(
            slot=publication.slot,
            publish_at_utc=publication.publish_at_utc,
        )
        await self.publication_repo.save(publication)

        await self.scheduler.schedule_publication(
            publication_id=publication.id,
            run_at_utc=publication.publish_at_utc,
        )

        await self.transaction_manager.commit()
