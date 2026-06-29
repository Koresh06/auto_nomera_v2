from dataclasses import dataclass

from src.application.exceptions.ad import AdNotFoundException
from src.application.exceptions.store import StoreItemsAlreadyExistException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.dtos.ad import AdDTO
from src.domain.value_objects.store_content import StoreContent, StoreItem
from src.infrastructure.database.transaction_manager.base import TransactionManager

@dataclass(frozen=True, eq=False)
class AddStoreItemsRequest(UseCaseRequest):
    ad_id: int
    items: list[StoreItem]


@dataclass(kw_only=True)
class AddStoreItemsUseCase(UseCase[AddStoreItemsRequest, "AddStoreItemsResult"]):
    ad_repo: AdRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: AddStoreItemsRequest) -> "AddStoreItemsResult":
        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None or ad.store_content is None:
            raise AdNotFoundException(command.ad_id)

        existing = ad.store_content
        existing_plates = {item.plate for item in existing.items}

        duplicates = [item.plate for item in command.items if item.plate in existing_plates]
        if duplicates:
            raise StoreItemsAlreadyExistException(duplicates)

        new_items = existing.items + tuple(command.items)
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

        return AddStoreItemsResult(
            ad=AdDTO.from_entity(ad),
            added_count=len(command.items),
        )


@dataclass(frozen=True, slots=True)
class AddStoreItemsResult:
    ad: AdDTO
    added_count: int