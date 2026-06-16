import logging
from dataclasses import dataclass

from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.tasks.task_queue import TaskQueue
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.ad import AdStatus
from src.domain.enums.publication import PublicationStatus
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ArchiveAdRequest(UseCaseRequest):
    ad_id: int
    publication_id: int | None = None  # None для urgent_buyout


@dataclass(kw_only=True)
class ArchiveAdUseCase(UseCase[ArchiveAdRequest, None]):
    ad_repo: AdRepository
    publication_repo: PublicationRepository
    task_queue: TaskQueue
    transaction_manager: TransactionManager

    async def __call__(self, command: ArchiveAdRequest) -> None:
        logger.info(
            "[ArchiveAd] ad_id=%s publication_id=%s",
            command.ad_id, command.publication_id,
        )

        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)

        ad.status = AdStatus.ARCHIVED
        await self.ad_repo.save(ad)

        if command.publication_id is not None:
            pub = await self.publication_repo.get_by_id(command.publication_id)
            if pub is not None:
                if pub.scheduler_job_id:
                    await self.task_queue.cancel(job_id=pub.scheduler_job_id)
                pub.status = PublicationStatus.CANCELED
                await self.publication_repo.save(pub)

        await self.transaction_manager.commit()

        logger.info("[ArchiveAd:done] ad_id=%s", command.ad_id)