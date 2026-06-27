import logging
from dataclasses import dataclass

from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.ad import AdType
from src.domain.services.ad.plate_validator import validate_plate
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class FinalizeAdRequest(UseCaseRequest):
    ad_id: int


@dataclass(kw_only=True)
class FinalizeAdUseCase(UseCase[FinalizeAdRequest, None]):
    ad_repo: AdRepository

    async def __call__(self, command: FinalizeAdRequest) -> None:
        logger.info(f"[FinalizeAd] ad_id={command.ad_id}")

        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)
        
        logger.info(f"[FinalizeAd] ad_type={ad.ad_type} content={ad.content}")

        if ad.ad_type == AdType.STORE:
            sc = ad.store_content
            if sc is None:
                raise ValueError("Store content is required")
            if not sc.shop_name:
                raise ValueError("Shop name required")
            if not sc.city:
                raise ValueError("City required")
            if not sc.contacts:
                raise ValueError("Contacts required")
            if len(sc.items) == 0:
                raise ValueError("At least one store item required")
            logger.info(f"[FinalizeAd:store] shop={sc.shop_name!r} items={len(sc.items)}")
            return

        if ad.content is None:
            raise ValueError("Ad content is required")

        c = ad.content
        if not c.plate_number:
            raise ValueError("Plate number is required")
        if not c.city:
            raise ValueError("City is required")
        if c.price is None:                      
            raise ValueError("Price is required") 
        if c.contacts is None:                     
            raise ValueError("Contacts are required")

        allow_mask = ad.ad_type == AdType.BUY
        validate_plate(c.plate_number, allow_mask=allow_mask)
        logger.info(
            f"[FinalizeAd:standard] plate={c.plate_number!r} city={c.city!r} "
            f"price={c.price.value} contacts={c.contacts.display!r}"
        )

        await self.ad_repo.save(ad)
        logger.info(f"[FinalizeAd:done] ad_id={ad.id}")
