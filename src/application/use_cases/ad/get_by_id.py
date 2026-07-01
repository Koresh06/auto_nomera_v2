import logging
from dataclasses import dataclass

from src.application.dtos.ad import AdDTO
from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.ad import Ad

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class GetByIdAdRequest(UseCaseRequest):
    ad_id: int


@dataclass(kw_only=True)
class GetByIdAdUseCase(UseCase[GetByIdAdRequest, AdDTO | None]):
    ad_repo: AdRepository

    async def __call__(self, command: GetByIdAdRequest) -> AdDTO | None:
        logger.info(f"[GetByIdAd] ad_id={command.ad_id}")

        ad: Ad | None = await self.ad_repo.get_by_id(command.ad_id)

        if ad is None:
            raise AdNotFoundException(command.ad_id)

        logger.info(f"[GetByIdAd:done] ad_id={ad.id}")
        return AdDTO.from_entity(ad)
