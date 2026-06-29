import logging
from dataclasses import dataclass

from src.domain.entities.ad import Ad
from src.domain.enums.ad import AdStatus, AdType
from src.application.dtos.ad import AdDTO
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class CreateAdDraftRequest(UseCaseRequest):
    user_id: int
    region_id: int
    ad_type: AdType
    status: AdStatus


@dataclass(kw_only=True)
class CreateAdDraftUseCase(UseCase[CreateAdDraftRequest, AdDTO]):
    ad_repo: AdRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: CreateAdDraftRequest) -> AdDTO:
        logger.info(
            f"[CreateAdDraft] user_id={command.user_id} "
            f"region_id={command.region_id} ad_type={command.ad_type}"
        )

        ad: Ad = await self.ad_repo.create(
            Ad(
                user_id=command.user_id,
                region_id=command.region_id,
                ad_type=command.ad_type,
                status=command.status,
            )
        )

        await self.transaction_manager.commit()

        logger.info(f"[CreateAdDraft:done] ad_id={ad.id}")
        return AdDTO.from_entity(ad)
