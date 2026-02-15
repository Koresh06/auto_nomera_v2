# src/infrastructure/dev/bootstrap.py
from __future__ import annotations
from datetime import time, timedelta


from src.application.mediator import Mediator

# ---------- domain ----------
from src.domain.entities.region import Region
from src.domain.enums.region import RegionStatus
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.slot_key import SlotKey

from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver


from src.application.use_cases.ad.create_ad_draft import CreateAdDraftUseCase, CreateAdDraftRequest
from src.application.use_cases.ad.update_ad_content import UpdateAdContentUseCase, UpdateAdContentRequest
from src.application.use_cases.ad.finalize_ad import FinalizeAdUseCase, FinalizeAdRequest
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdUseCase,
    CreatePublicationFromAdRequest,
)

from src.application.use_cases.slots.get_calendar import GetCalendarUseCase, GetCalendarRequest
from src.application.use_cases.publication.select_slot_for_publication import (
    SelectSlotForPublicationUseCase,
    SelectSlotForPublicationRequest,
)

from src.infrastructure.dev.repos import InMemoryAdRepo, InMemoryPublicationRepo, InMemoryRegionRepo
from src.infrastructure.dev.scheduler import DevScheduler
from src.infrastructure.dev.slots_mem import InMemorySlotBookingRepo, InMemorySlotConvertedRepo, InMemorySlotHoldStore



def build_dev_container() -> Mediator:
    """
    Собирает мок-окружение (in-memory) + регистрирует use-cases в Mediator.
    Никакого Dishka тут нет — просто фабрика.
    """
    # 1) мок регионы
    region_1 = Region(
        id=1,
        title="Минск",
        timezone=TimezoneName("Europe/Minsk"),
        channel_id=-100123456789,  # любой тестовый
        status=RegionStatus.ACTIVE,
        settings=RegionSettings(),
        metadata=RegionMetadata(
            data={
                "channel_username": "my_region_channel",
                "tg_group_url": "https://t.me/avtonomera126_26",
                "vk_group_url": "https://vk.com/26gosnomera126",
            }
        ),
    )

    # 2) репозитории
    ad_repo = InMemoryAdRepo()
    pub_repo = InMemoryPublicationRepo()
    region_repo = InMemoryRegionRepo([region_1])

    hold_store = InMemorySlotHoldStore()
    booking_repo = InMemorySlotBookingRepo()
    converted_repo = InMemorySlotConvertedRepo()

    # 3) доменные сервисы
    calendar_builder = CalendarBuilder()
    pricing_policy = SlotPricingPolicy(system_paid_count=3)
    reservation_service = SlotReservationService(
        booking_repo=booking_repo,
        converted_repo=converted_repo,
        hold_store=hold_store,
        pricing_policy=pricing_policy,
        hold_ttl=timedelta(minutes=15),
    )
    time_resolver = PublishTimeResolver()

    # 4) scheduler
    scheduler = DevScheduler()

    # 5) mediator + регистрации
    mediator = Mediator()

    mediator.register(CreateAdDraftRequest, CreateAdDraftUseCase(ad_repo=ad_repo))
    mediator.register(UpdateAdContentRequest, UpdateAdContentUseCase(ad_repo=ad_repo))
    mediator.register(FinalizeAdRequest, FinalizeAdUseCase(ad_repo=ad_repo, region_repo=region_repo))
    mediator.register(
        CreatePublicationFromAdRequest,
        CreatePublicationFromAdUseCase(ad_repo=ad_repo, publication_repo=pub_repo),
    )

    mediator.register(
        GetCalendarRequest,
        GetCalendarUseCase(
            region_repo=region_repo,
            booking_repo=booking_repo,
            converted_repo=converted_repo,
            hold_store=hold_store,
            calendar_builder=calendar_builder,
        ),
    )

    mediator.register(
        SelectSlotForPublicationRequest,
        SelectSlotForPublicationUseCase(
            publication_repo=pub_repo,
            region_repo=region_repo,
            scheduler=scheduler,
            calendar_builder=calendar_builder,
            time_resolver=time_resolver,
            reservation_service=reservation_service,
            pricing_policy=pricing_policy,
        ),
    )

    return mediator
