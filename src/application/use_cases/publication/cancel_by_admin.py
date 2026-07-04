import logging
from dataclasses import dataclass

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.tasks.task_queue import TaskQueue
from src.application.services.notification.notification_service import (
    NotificationService,
)
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.publication import PublicationStatus
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class CancelPublicationByAdminRequest(UseCaseRequest):
    publication_id: int
    owner_tg_id: int
    label: str


@dataclass(kw_only=True)
class CancelPublicationByAdminUseCase(UseCase[CancelPublicationByAdminRequest, None]):
    publication_repo: PublicationRepository
    task_queue: TaskQueue
    notification_service: NotificationService
    transaction_manager: TransactionManager

    async def __call__(self, command) -> None:
        pub = await self.publication_repo.get_by_id(command.publication_id)
        if pub is None:
            raise PublicationNotFoundException(command.publication_id)

        series = await self.publication_repo.list_scheduled_by_ad(pub.ad_id)
        for p in series:
            if p.status not in (
                PublicationStatus.SCHEDULED,
                PublicationStatus.AWAITING_PAYMENT,
                PublicationStatus.DRAFT,
            ):
                continue
            if p.scheduler_job_id:
                await self.task_queue.cancel(job_id=p.scheduler_job_id)
            p.cancel()
            await self.publication_repo.save(p)

        await self.transaction_manager.commit()

        await self.notification_service.notify_user(
            tg_id=command.owner_tg_id,
            text=f"⚠️ Ваша публикация {command.label} отменена администратором.",
        )
