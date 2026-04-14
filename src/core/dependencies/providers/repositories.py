from dishka import Provider, Scope, provide

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
from src.infrastructure.repositories.publication.in_memory import (
    InMemoryPublicationRepo,
)
from src.infrastructure.repositories.region.in_memory import (
    InMemoryRegionRepo,
    region_1,
)
from src.infrastructure.repositories.service_def.in_memory import (
    InMemoryServiceDefinitionRepository,
)
from src.infrastructure.repositories.slot.in_memory import (
    InMemorySlotBookingRepo,
    InMemorySlotConvertedRepo,
)
from src.infrastructure.repositories.user.in_memory import InMemoryUserRepo
from src.infrastructure.slots.holt_store.in_memory import InMemorySlotHoldStore


class RepositoriesProvider(Provider):
    scope = Scope.APP

    @provide
    def get_user_repository(self) -> UserRepository:
        return InMemoryUserRepo()

    @provide
    def get_region_repository(self) -> RegionRepository:
        return InMemoryRegionRepo(regions=[region_1])

    @provide
    def get_ad_repository(self) -> AdRepository:
        return InMemoryAdRepo()

    @provide
    def get_publication_repository(self) -> PublicationRepository:
        return InMemoryPublicationRepo()

    @provide
    def get_slot_booking_repository(self) -> SlotBookingRepository:
        return InMemorySlotBookingRepo()

    @provide
    def get_slot_converted_repository(self) -> SlotConvertedRepository:
        return InMemorySlotConvertedRepo()
    
    @provide
    def get_slot_hold_store(self) -> SlotHoldStore:
        return InMemorySlotHoldStore()

    @provide
    def get_service_definition_repository(self) -> ServiceDefinitionRepository:
        return InMemoryServiceDefinitionRepository()
