import logging
from dataclasses import dataclass

from src.application.exceptions.ad import AdAlreadyProcessedException, AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.ad import AdStatus
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class RejectUrgentBuyoutRequest(UseCaseRequest):
    ad_id: int


@dataclass(kw_only=True)
class RejectUrgentBuyoutUseCase(UseCase[RejectUrgentBuyoutRequest, None]):
    ad_repo: AdRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: RejectUrgentBuyoutRequest) -> None:
        logger.info("[RejectUrgentBuyout] ad_id=%s", command.ad_id)

        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)

        if ad.status != AdStatus.PENDING_MODERATION:
            raise AdAlreadyProcessedException(command.ad_id)

        ad.status = AdStatus.ARCHIVED
        await self.ad_repo.save(ad)
        await self.transaction_manager.commit()

        logger.info("[RejectUrgentBuyout:done] ad_id=%s", command.ad_id)