import logging
from dataclasses import dataclass

from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.dtos.ad import AdDTO
from src.domain.entities.ad import Ad
from src.domain.enums.ad import AdStatus, AdType
from src.domain.services.region.region_guard import RegionGuard
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.store_content import StoreContent
from src.infrastructure.database.transaction_manager.base import TransactionManager
from src.application.exceptions.store import StoreAlreadyExistsException


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class CreateStoreRequest(UseCaseRequest):
    user_id: int
    region_id: int
    shop_name: str
    city: str
    contacts: Contacts


@dataclass(kw_only=True)
class CreateStoreUseCase(UseCase[CreateStoreRequest, AdDTO]):
    region_guard: RegionGuard
    ad_repo: AdRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: CreateStoreRequest) -> AdDTO:
        await self.region_guard.ensure_active(command.region_id)
        existing = await self.ad_repo.find_store_by_user(
            user_id=command.user_id,
            region_id=command.region_id,
        )
        if existing is not None:
            raise StoreAlreadyExistsException(existing.id)

        ad = await self.ad_repo.create(
            Ad(
                user_id=command.user_id,
                region_id=command.region_id,
                ad_type=AdType.STORE,
                status=AdStatus.DRAFT,
            )
        )
        ad.fill_store_content(
            StoreContent(
                shop_name=command.shop_name,
                city=command.city,
                contacts=command.contacts,
                items=(),
            )
        )
        await self.ad_repo.save(ad)
        await self.transaction_manager.commit()

        return AdDTO.from_entity(ad)