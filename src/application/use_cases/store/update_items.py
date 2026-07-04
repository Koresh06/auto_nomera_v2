import logging
from dataclasses import dataclass

from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.dtos.ad import AdDTO
from src.domain.value_objects.price import Price
from src.domain.value_objects.store_content import StoreContent, StoreItem
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class UpdateStoreItemRequest(UseCaseRequest):
    ad_id: int
    plate: str
    new_plate: str | None = None
    new_price: int | None = None


@dataclass(kw_only=True)
class UpdateStoreItemUseCase(UseCase[UpdateStoreItemRequest, AdDTO]):
    ad_repo: AdRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: UpdateStoreItemRequest) -> AdDTO:
        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None or ad.store_content is None:
            raise AdNotFoundException(command.ad_id)

        existing = ad.store_content
        new_items = []
        for item in existing.items:
            if item.plate == command.plate:
                new_items.append(
                    StoreItem(
                        plate=command.new_plate or item.plate,
                        price=(
                            Price(command.new_price)
                            if command.new_price is not None
                            else item.price
                        ),
                    )
                )
            else:
                new_items.append(item)

        ad.fill_store_content(
            StoreContent(
                shop_name=existing.shop_name,
                city=existing.city,
                contacts=existing.contacts,
                items=tuple(new_items),
            )
        )
        await self.ad_repo.save(ad)
        await self.transaction_manager.commit()
        logger.info("[UpdateStoreItem:done] ad_id=%s", command.ad_id)

        return AdDTO.from_entity(ad)
