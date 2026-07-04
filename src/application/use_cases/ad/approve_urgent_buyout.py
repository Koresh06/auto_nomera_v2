import logging
from dataclasses import dataclass

from src.application.exceptions.ad import (
    AdAlreadyProcessedException,
    AdNotFoundException,
)
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.tasks.task_queue import TaskQueue
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.ad import AdStatus
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ApproveUrgentBuyoutRequest(UseCaseRequest):
    ad_id: int


@dataclass(kw_only=True)
class ApproveUrgentBuyoutUseCase(UseCase[ApproveUrgentBuyoutRequest, None]):
    ad_repo: AdRepository
    task_queue: TaskQueue
    transaction_manager: TransactionManager

    async def __call__(self, command: ApproveUrgentBuyoutRequest) -> None:
        logger.info("[ApproveUrgentBuyout] ad_id=%s", command.ad_id)

        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)

        if ad.status != AdStatus.PENDING_MODERATION:
            raise AdAlreadyProcessedException(command.ad_id)

        ad.status = AdStatus.PUBLISHED
        await self.ad_repo.save(ad)
        await self.transaction_manager.commit()

        await self.task_queue.enqueue(
            task_name="notify_pre_publication_users",
            args=(command.ad_id,),
        )

        logger.info("[ApproveUrgentBuyout:done] ad_id=%s", command.ad_id)
