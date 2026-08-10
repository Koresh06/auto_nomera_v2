from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.ports.tasks.task_queue import TaskQueue
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.core.config import AppSettings
from src.domain.entities.publication import Publication
from src.domain.enums.publication import PublicationStatus
from src.domain.exceptions.publication import InvalidPublicationState
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


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
    task_queue: TaskQueue
    settings: AppSettings
    transaction_manager: TransactionManager

    async def __call__(
        self, command: ConfirmPaidSlotAndSchedulePublicationRequest
    ) -> None:
        publication = await self.publication_repo.get_by_id(command.publication_id)
        if publication is None:
            raise PublicationNotFoundException(command.publication_id)

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

        await self.reservation_service.book_after_payment(
            slot=publication.slot,
            user_id=command.user_id,
            ad_id=command.ad_id,
            require_hold_owner=False,
        )

        publication.schedule(
            slot=publication.slot,
            publish_at_utc=publication.publish_at_utc,
        )
        await self.publication_repo.save(publication)
        await self.scheduler.schedule_publication(
            publication_id=publication.id,
            run_at_utc=publication.publish_at_utc,
        )

        # schedule_publication commits its own transaction and sets scheduler_job_id
        # via a separate entity instance. Reload so the entity below carries the
        # freshly-written scheduler_job_id; otherwise the subsequent save() inside
        # _schedule_pre_publication_notification overwrites scheduler_job_id to None.
        publication = await self.publication_repo.get_by_id(publication.id)

        await self._schedule_pre_publication_notification(
            ad_id=command.ad_id,
            publish_at_utc=publication.publish_at_utc,
            publication=publication,
        )
        await self.transaction_manager.commit()

    async def _schedule_pre_publication_notification(
        self,
        *,
        ad_id: int,
        publish_at_utc: datetime,
        publication: Publication,
    ) -> None:
        if self.settings.app.debug:
            notify_at = publish_at_utc - timedelta(minutes=1)
        else:
            notify_at = publish_at_utc - timedelta(
                hours=self.settings.app.pre_publication_window_hours
            )

        now = datetime.now(timezone.utc)
        if notify_at <= now:
            logger.info(f"[SelectSlot:notify_skip] ad_id={ad_id} ...")
            return

        await self.task_queue.schedule(
            task_name="notify_pre_publication_users",
            args=(ad_id,),
            run_at_utc=notify_at,
        )
        publication.notify_scheduled = True
        await self.publication_repo.save(publication)

        logger.info(
            f"[SelectSlot:notify_scheduled] ad_id={ad_id} notify_at={notify_at}"
        )
