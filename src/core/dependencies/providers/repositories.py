from dishka import Provider, Scope, provide

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication_service.service_definition_repo import (
    ServiceDefinitionRepository,
)
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.application.ports.user.user_repo import UserRepository
from src.infrastructure.repositories.ad.in_memory import InMemoryAdRepo
from src.infrastructure.repositories.ad.sqlalchemy import SQLAlchemyAdRepo
from src.infrastructure.repositories.publication.in_memory import (
    InMemoryPublicationRepo,
)
from src.infrastructure.repositories.publication.sqlalchemy import SQLAlchemyPublicationRepo
from src.infrastructure.repositories.region.in_memory import (
    InMemoryRegionRepo,
    region_1,
)
from src.infrastructure.repositories.region.sqlalchemy import SQLAlchemyRegionRepository
from src.infrastructure.repositories.service_def.in_memory import (
    InMemoryServiceDefinitionRepository,
)
from src.infrastructure.repositories.service_def.sqlalchemy import SQLAlchemyServiceDefinitionRepo
from src.infrastructure.repositories.slot.in_memory import (
    InMemorySlotBookingRepo,
    InMemorySlotConvertedRepo,
)
from src.infrastructure.repositories.slot.sqlalchemy import SQLAlchemySlotBookingRepo, SQLAlchemySlotConvertedRepo
from src.infrastructure.repositories.user.in_memory import InMemoryUserRepo
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo
from src.infrastructure.slots.holt_store.in_memory import InMemorySlotHoldStore


class RepositoriesProvider(Provider):

    @provide(scope=Scope.APP)
    def get_slot_hold_store(self) -> SlotHoldStore:
        return InMemorySlotHoldStore()

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        return SQLAlchemyUserRepo(session)

    @provide(scope=Scope.REQUEST)
    def get_region_repository(self, session: AsyncSession) -> RegionRepository:
        return SQLAlchemyRegionRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_ad_repository(self, session: AsyncSession) -> AdRepository:
        return SQLAlchemyAdRepo(session)

    @provide(scope=Scope.REQUEST)
    def get_publication_repository(self, session: AsyncSession) -> PublicationRepository:
        return SQLAlchemyPublicationRepo(session)

    @provide(scope=Scope.REQUEST)
    def get_slot_booking_repository(self, session: AsyncSession) -> SlotBookingRepository:
        return SQLAlchemySlotBookingRepo(session)

    @provide(scope=Scope.REQUEST)
    def get_slot_converted_repository(self, session: AsyncSession) -> SlotConvertedRepository:
        return SQLAlchemySlotConvertedRepo(session)

    @provide(scope=Scope.REQUEST)
    def get_service_definition_repository(self, session: AsyncSession) -> ServiceDefinitionRepository:
        return SQLAlchemyServiceDefinitionRepo(session)
