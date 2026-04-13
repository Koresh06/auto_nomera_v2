from dishka import Provider, provide, Scope

from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.ports.publication_service.image_processor import ImageProcessor
from src.application.ports.publication_service.service_definition_repo import (
    ServiceDefinitionRepository,
)
from src.application.ports.telegram.telegram_publisher import TelegramPublisher
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.ad.create_ad_draft import CreateAdDraftUseCase
from src.application.use_cases.ad.ensure_ad_image_ref import EnsureAdImageRefUseCase
from src.application.use_cases.ad.finalize_ad import FinalizeAdUseCase
from src.application.use_cases.ad.update_ad_content import UpdateAdContentUseCase
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdUseCase,
)
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationUseCase,
)
from src.application.use_cases.publication_service.add_service_to_publication import (
    AddServiceToPublicationUseCase,
)
from src.application.use_cases.publication_service.priority_publish_publication import (
    PriorityPublishPublicationUseCase,
)
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.application.use_cases.publication.confirm_paid_slot_and_schedule_publication import (
    ConfirmPaidSlotAndSchedulePublicationUseCase,
)
from src.application.use_cases.publication.select_slot_for_publication import (
    SelectSlotForPublicationUseCase,
)
from src.application.use_cases.publication_service.unpin_message import (
    UnpinMessageUseCase,
)
from src.application.use_cases.region.get_all import GetAllRegionsUseCase
from src.application.use_cases.slots.get_calendar import GetCalendarUseCase
from src.application.use_cases.slots.hold_slot import HoldSlotUseCase
from src.application.use_cases.user.get_by_tg_id import GetByTgIdUserUseCase
from src.application.use_cases.user.register_user import RegisterUserUseCase
from src.application.use_cases.user.update import UpdateUserUseCase
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.services.slots.slot_reservation_service import SlotReservationService


class UseCasesProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def register_user_use_case(
        self,
        user_repo: UserRepository,
    ) -> RegisterUserUseCase:
        return RegisterUserUseCase(user_repo=user_repo)

    @provide
    def get_by_tg_id_user_use_case(
        self,
        user_repo: UserRepository,
    ) -> GetByTgIdUserUseCase:
        return GetByTgIdUserUseCase(user_repo=user_repo)
    

    @provide
    def update_user_use_case(
        self,
        user_repo: UserRepository,
    ) -> UpdateUserUseCase:
        return UpdateUserUseCase(user_repo=user_repo)


    @provide
    def get_all_region_use_case(
        self,
        region_repo: RegionRepository,
    ) -> GetAllRegionsUseCase:
        return GetAllRegionsUseCase(region_repo=region_repo)

    @provide
    def get_caledar_use_case(
        self,
        region_repo: RegionRepository,
        booking_repo: SlotBookingRepository,
        converted_repo: SlotConvertedRepository,
        hold_store: SlotHoldStore,
        calendar_builder: CalendarBuilder,
    ) -> GetCalendarUseCase:
        return GetCalendarUseCase(
            region_repo=region_repo,
            booking_repo=booking_repo,
            converted_repo=converted_repo,
            hold_store=hold_store,
            calendar_builder=calendar_builder,
        )

    @provide
    def hold_slot_use_case(
        self,
        region_repo: RegionRepository,
        calendar_builder: CalendarBuilder,
        reservation_service: SlotReservationService,
    ) -> HoldSlotUseCase:
        return HoldSlotUseCase(
            region_repo=region_repo,
            calendar_builder=calendar_builder,
            reservation_service=reservation_service,
        )

    @provide
    def confirm_paid_slot_and_schedule_publication_use_case(
        self,
        publication_repo: PublicationRepository,
        scheduler: Scheduler,
        reservation_service: SlotReservationService,
    ) -> ConfirmPaidSlotAndSchedulePublicationUseCase:
        return ConfirmPaidSlotAndSchedulePublicationUseCase(
            publication_repo=publication_repo,
            scheduler=scheduler,
            reservation_service=reservation_service,
        )

    @provide
    def select_slot_for_publication_use_case(
        self,
        publication_repo: PublicationRepository,
        region_repo: RegionRepository,
        scheduler: Scheduler,
        calendar_builder: CalendarBuilder,
        time_resolver: PublishTimeResolver,
        reservation_service: SlotReservationService,
        pricing_policy: SlotPricingPolicy,
    ) -> SelectSlotForPublicationUseCase:
        return SelectSlotForPublicationUseCase(
            publication_repo=publication_repo,
            region_repo=region_repo,
            scheduler=scheduler,
            calendar_builder=calendar_builder,
            time_resolver=time_resolver,
            reservation_service=reservation_service,
            pricing_policy=pricing_policy,
        )

    @provide
    def add_service_to_publication_use_case(
        self,
        publication_repo: PublicationRepository,
        service_def_repo: ServiceDefinitionRepository,
    ) -> AddServiceToPublicationUseCase:
        return AddServiceToPublicationUseCase(
            publication_repo=publication_repo,
            service_def_repo=service_def_repo,
        )

    @provide
    def priority_publish_publication_use_case(
        self,
        publication_repo: PublicationRepository,
        scheduler: Scheduler,
    ) -> PriorityPublishPublicationUseCase:
        return PriorityPublishPublicationUseCase(
            publication_repo=publication_repo,
            scheduler=scheduler,
        )

    @provide
    def publish_publication_use_case(
        self,
        publication_repo: PublicationRepository,
        ad_repo: AdRepository,
        region_repo: RegionRepository,
        telegram: TelegramPublisher,
        image_processor: ImageProcessor,
        scheduler: Scheduler,
        renderer: AdTextRenderer,
        time_resolver: PublishTimeResolver,
    ) -> PublishPublicationUseCase:
        return PublishPublicationUseCase(
            publication_repo=publication_repo,
            ad_repo=ad_repo,
            region_repo=region_repo,
            telegram=telegram,
            image_processor=image_processor,
            scheduler=scheduler,
            renderer=renderer,
            time_resolver=time_resolver,
        )

    @provide
    def unpin_message_use_case(
        self,
        telegram: TelegramPublisher,
    ) -> UnpinMessageUseCase:
        return UnpinMessageUseCase(telegram=telegram)

    @provide
    def ensure_ad_image_ref_use_case(
        self,
        ad_repo: AdRepository,
        region_repo: RegionRepository,
    ) -> EnsureAdImageRefUseCase:
        return EnsureAdImageRefUseCase(
            ad_repo=ad_repo,
            region_repo=region_repo,
        )

    @provide
    def create_ad_draft_use_case(self, ad_repo: AdRepository) -> CreateAdDraftUseCase:
        return CreateAdDraftUseCase(ad_repo=ad_repo)

    @provide
    def update_ad_content_use_case(
        self,
        ad_repo: AdRepository,
    ) -> UpdateAdContentUseCase:
        return UpdateAdContentUseCase(ad_repo=ad_repo)

    @provide
    def finalize_ad_use_case(
        self,
        ad_repo: AdRepository,
        region_repo: RegionRepository,
    ) -> FinalizeAdUseCase:
        return FinalizeAdUseCase(
            ad_repo=ad_repo,
            region_repo=region_repo,
        )

    @provide
    def create_publication_from_ad_use_case(
        self,
        ad_repo: AdRepository,
        publication_repo: PublicationRepository,
    ) -> CreatePublicationFromAdUseCase:
        return CreatePublicationFromAdUseCase(
            ad_repo=ad_repo,
            publication_repo=publication_repo,
        )
