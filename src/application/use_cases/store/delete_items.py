import logging
from dataclasses import dataclass

from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.dtos.ad import AdDTO
from src.domain.value_objects.store_content import StoreContent
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class DeleteStoreItemRequest(UseCaseRequest):
    ad_id: int
    plate: str


@dataclass(kw_only=True)
class DeleteStoreItemUseCase(UseCase[DeleteStoreItemRequest, AdDTO]):
    ad_repo: AdRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: DeleteStoreItemRequest) -> AdDTO:
        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None or ad.store_content is None:
            raise AdNotFoundException(command.ad_id)

        existing = ad.store_content
        new_items = tuple(i for i in existing.items if i.plate != command.plate)

        ad.fill_store_content(
            StoreContent(
                shop_name=existing.shop_name,
                city=existing.city,
                contacts=existing.contacts,
                items=new_items,
            )
        )
        await self.ad_repo.save(ad)
        await self.transaction_manager.commit()
        logger.info("[DeleteStoreItem:done] ad_id=%s", command.ad_id)

        return AdDTO.from_entity(ad)
