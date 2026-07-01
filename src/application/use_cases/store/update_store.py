import logging
from dataclasses import dataclass

from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.dtos.ad import AdDTO
from src.domain.entities.ad import Ad
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.store_content import StoreContent
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class UpdateStoreRequest(UseCaseRequest):
    ad_id: int
    shop_name: str | None = None
    city: str | None = None
    contacts: Contacts | None = None


@dataclass(kw_only=True)
class UpdateStoreUseCase(UseCase[UpdateStoreRequest, AdDTO]):
    ad_repo: AdRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: UpdateStoreRequest) -> AdDTO:
        ad: Ad | None = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None or ad.store_content is None:
            raise AdNotFoundException(command.ad_id)

        existing = ad.store_content
        ad.fill_store_content(
            StoreContent(
                shop_name=command.shop_name or existing.shop_name,
                city=command.city or existing.city,
                contacts=command.contacts or existing.contacts,
                items=existing.items,
            )
        )
        await self.ad_repo.save(ad)
        await self.transaction_manager.commit()

        logger.info("[UpdateStore:done] ad_id=%s", command.ad_id)

        return AdDTO.from_entity(ad)
