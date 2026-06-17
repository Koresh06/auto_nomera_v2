import logging
from dataclasses import dataclass

from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class CountAdsByUserRequest(UseCaseRequest):
    user_id: int
    region_id: int


@dataclass(kw_only=True)
class CountAdsByUserUseCase(UseCase[CountAdsByUserRequest, int]):
    ad_repo: AdRepository

    async def __call__(self, command: CountAdsByUserRequest) -> int:
        logger.info(
            "[CountAdsByUser] user_id=%s region_id=%s",
            command.user_id, command.region_id,
        )
        count = await self.ad_repo.count_ads_by_user(
            user_id=command.user_id,
            region_id=command.region_id,
        )
        logger.info("[CountAdsByUser:done] count=%s", count)
        return count