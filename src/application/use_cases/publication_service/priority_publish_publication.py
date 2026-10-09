from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.publication import Publication
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.exceptions.publication import InvalidPublicationState
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

        service = next(
            (
                s
                for s in publication.services
                if s.type == PublicationServiceType.PRIORITY_PUBLISH
                and s.status == PublicationServiceStatus.ACTIVE
            ),
            None,
        )

        if publication.status == PublicationStatus.SCHEDULED:
            await self.scheduler.cancel_publication(publication_id=publication.id)
            await self.scheduler.schedule_publish_now(publication_id=publication.id)

            if service:
                # Планировщик сохранил новый scheduler_job_id через свою копию
                # публикации. Сохранение нашей (загруженной до отмены) копии
                # вернуло бы в БД id уже отменённой задачи — и последующая
                # отмена публикации не сняла бы реальную немедленную задачу.
                publication = await self.publication_repo.get_by_id(publication.id)
                service = next(
                    s
                    for s in publication.services
                    if s.type == PublicationServiceType.PRIORITY_PUBLISH
                    and s.status == PublicationServiceStatus.ACTIVE
                )
                service.mark_used()
                await self.publication_repo.save(publication)

            await self.transaction_manager.commit()

        elif publication.status == PublicationStatus.PUBLISHED:
            new_pub = Publication(
                ad_id=publication.ad_id,
                region_id=publication.region_id,
                is_child=True,
            )
            new_pub.schedule_immediate(publish_at_utc=datetime.now(timezone.utc))
            new_pub = await self.publication_repo.create(new_pub)

            if service:
                service.mark_used()
                await self.publication_repo.save(publication)

            # СНАЧАЛА коммит, потом очередь
            await self.transaction_manager.commit()

            await self.scheduler.schedule_publish_now(publication_id=new_pub.id)
            await self.transaction_manager.commit()

        else:
            raise InvalidPublicationState(
                f"PRIORITY_PUBLISH нельзя применить к публикации в статусе {publication.status}"
            )
