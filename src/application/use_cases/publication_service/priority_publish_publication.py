from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType


@dataclass(frozen=True, eq=False)
class PriorityPublishPublicationRequest(UseCaseRequest):
    publication_id: int
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class PriorityPublishPublicationUseCase(UseCase[PriorityPublishPublicationRequest, None]):
    publication_repo: PublicationRepository
    scheduler: Scheduler

    async def __call__(self, command: PriorityPublishPublicationRequest) -> None:
        _ = command.now_utc or datetime.now(timezone.utc)

        publication = await self.publication_repo.get_by_id(command.publication_id)

        # 1) добавляем услугу PRIORITY (если ещё нет) — чтобы воркер знал контекст
        if not publication.has_service(PublicationServiceType.PRIORITY_PUBLISH):
            publication.add_service(PublicationService(type=PublicationServiceType.PRIORITY_PUBLISH))

        # 2) если было запланировано — отменяем задачу и помечаем как REPLACED
        if publication.status == PublicationStatus.SCHEDULED:
            await self.scheduler.cancel_publication(publication_id=publication.id)
            publication.mark_replaced_by_priority()
            await self.publication_repo.save(publication)

        # 3) ставим задачу "publish now"
        await self.scheduler.schedule_publish_now(publication_id=publication.id)
