from src.application.mediator import Mediator

from src.application.use_cases.region.get_all import (
    GetAllRegionsUseCase,
    GetRegionsRequest,
)
from src.application.use_cases.user.get_by_tg_id import (
    GetByTgIdUserUseCase,
    GetTgIdRequest,
)
from src.domain.entities.region import Region
from src.domain.enums.region import RegionStatus

from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName
from src.domain.value_objects.region_metadata import RegionMetadata


from src.infrastructure.repositories.region.in_memory import InMemoryRegionRepo
from src.infrastructure.repositories.user.in_memory import InMemoryUserRepo


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
        channel_id=-100123456789,
        channel_username="avtonomera126_26",
        status=RegionStatus.ACTIVE,
        settings=RegionSettings(),
        metadata=RegionMetadata(
            data={
                "tg_group_url": "https://t.me/avtonomera126_26",
                "vk_group_url": "https://vk.com/26gosnomera126",
                "max_channel_url": "https://t.me/avtonomera126_26",
            }
        ),
    )

    # 2) репозитории
    # ad_repo = InMemoryAdRepo()
    # pub_repo = InMemoryPublicationRepo()
    user_repo = InMemoryUserRepo()
    region_repo = InMemoryRegionRepo([region_1])

    # hold_store = InMemorySlotHoldStore()
    # booking_repo = InMemorySlotBookingRepo()
    # converted_repo = InMemorySlotConvertedRepo()

    # # 3) доменные сервисы
    # calendar_builder = CalendarBuilder()
    # pricing_policy = SlotPricingPolicy(system_paid_count=3)
    # reservation_service = SlotReservationService(
    #     booking_repo=booking_repo,
    #     converted_repo=converted_repo,
    #     hold_store=hold_store,
    #     pricing_policy=pricing_policy,
    #     hold_ttl=timedelta(minutes=15),
    # )
    # time_resolver = PublishTimeResolver()

    # # 4) scheduler
    # scheduler = DevScheduler()

    # 5) mediator + регистрации
    mediator = Mediator()

    mediator.register(GetTgIdRequest, GetByTgIdUserUseCase(user_repo=user_repo))
    mediator.register(GetRegionsRequest, GetAllRegionsUseCase(region_repo=region_repo))
    # mediator.register(CreateAdDraftRequest, CreateAdDraftUseCase(ad_repo=ad_repo))
    # mediator.register(UpdateAdContentRequest, UpdateAdContentUseCase(ad_repo=ad_repo))
    # mediator.register(FinalizeAdRequest, FinalizeAdUseCase(ad_repo=ad_repo, region_repo=region_repo))
    # mediator.register(
    #     CreatePublicationFromAdRequest,
    #     CreatePublicationFromAdUseCase(ad_repo=ad_repo, publication_repo=pub_repo),
    # )

    # mediator.register(
    #     GetCalendarRequest,
    #     GetCalendarUseCase(
    #         region_repo=region_repo,
    #         booking_repo=booking_repo,
    #         converted_repo=converted_repo,
    #         hold_store=hold_store,
    #         calendar_builder=calendar_builder,
    #     ),
    # )

    # mediator.register(
    #     SelectSlotForPublicationRequest,
    #     SelectSlotForPublicationUseCase(
    #         publication_repo=pub_repo,
    #         region_repo=region_repo,
    #         scheduler=scheduler,
    #         calendar_builder=calendar_builder,
    #         time_resolver=time_resolver,
    #         reservation_service=reservation_service,
    #         pricing_policy=pricing_policy,
    #     ),
    # )

    return mediator
