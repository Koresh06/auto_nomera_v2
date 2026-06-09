from dataclasses import dataclass
from datetime import datetime

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class PriorityPublishPublicationRequest(UseCaseRequest):
    publication_id: int
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class PriorityPublishPublicationUseCase(
    UseCase[PriorityPublishPublicationRequest, None]
):
    publication_repo: PublicationRepository
    scheduler: Scheduler
    transaction_manager: TransactionManager

    async def __call__(self, command: PriorityPublishPublicationRequest) -> None:
        publication = await self.publication_repo.get_by_id(command.publication_id)
        if publication is None:
            raise PublicationNotFoundException(command.publication_id)
    
        # отменяем старую задачу из планировщика
        if publication.status == PublicationStatus.SCHEDULED:
            await self.scheduler.cancel_publication(publication_id=publication.id)
    
        # НЕ меняем статус — оставляем SCHEDULED
        # ставим задачу немедленно
        await self.scheduler.schedule_publish_now(publication_id=publication.id)
    
        await self.publication_repo.save(publication)
        await self.transaction_manager.commit()
