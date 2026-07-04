import logging

from src.application.ports.region.region_repo import RegionRepository
from src.domain.entities.region import Region
from src.domain.enums.region import RegionStatus
from src.domain.exceptions.region import RegionDisabledError, RegionNotFoundException


logger = logging.getLogger(__name__)


class RegionGuard:
    def __init__(self, region_repo: RegionRepository) -> None:
        self.region_repo = region_repo

    async def ensure_active(self, region_id: int) -> Region:
        region = await self.region_repo.get_by_id(region_id)
        if region is None:
            raise RegionNotFoundException(region_id)
        if region.status != RegionStatus.ACTIVE:
            logger.info("Region %s is disabled", region.title)
            raise RegionDisabledError(region_id)
        return region
