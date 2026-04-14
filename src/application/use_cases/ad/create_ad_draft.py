from dataclasses import dataclass
import logging

from src.application.dtos.ad import AdDTO
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.ad import Ad
from src.domain.enums.ad import AdType


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class CreateAdDraftRequest(UseCaseRequest):
    user_id: int
    region_id: int
    ad_type: AdType


@dataclass(kw_only=True)
class CreateAdDraftUseCase(UseCase[CreateAdDraftRequest, AdDTO]):
    ad_repo: AdRepository

    async def __call__(self, command: CreateAdDraftRequest) -> AdDTO:
        logger.info(
            f"[CreateAdDraft] user_id={command.user_id} "
            f"region_id={command.region_id} ad_type={command.ad_type}"
        )

        ad = Ad(
            user_id=command.user_id,
            region_id=command.region_id,
            ad_type=command.ad_type,
        )
        await self.ad_repo.create(ad)

        logger.info(f"[CreateAdDraft:done] ad_id={ad.id}")
        return AdDTO.from_entity(ad)


