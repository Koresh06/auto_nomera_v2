from aiogram import Bot
from dishka import Provider, provide, Scope

from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.cache.block import BlockCache
from src.application.ports.dialog.teleport import DialogTeleporter
from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.use_cases.miling.enqueue import EnqueueMailingUseCase
from src.application.use_cases.miling.execute import ExecuteMailingUseCase
from src.application.use_cases.publication.cancel_by_admin import (
    CancelPublicationByAdminUseCase,
)
from src.application.use_cases.publication.get_admin_scheduled_catalog import (
    GetAdminScheduledCatalogUseCase,
)
from src.application.use_cases.region.toggle_status import ToggleRegionStatusUseCase
from src.application.use_cases.region.update_metadata import UpdateRegionMetadataUseCase
from src.application.use_cases.region.update_settings import UpdateRegionSettingsUseCase
from src.application.use_cases.service_difinition.toggle_status import (
    ToggleServiceStatusUseCase,
)
from src.application.use_cases.service_difinition.update import UpdateServiceUseCase
from src.application.use_cases.slots.confirm_paid_slot_from_balance import (
    ConfirmPaidSlotFromBalanceUseCase,
)
from src.application.services.payment.provider_registry import PaymentProviderRegistry
from src.application.use_cases.payment.get_by_external_id import (
    GetPaymentByExternalIdUseCase,
)
from src.application.use_cases.payment.mark import MarkPaymentFailedUseCase
from src.application.use_cases.publication.finalize_and_schedule_existing_ad import (
    FinalizeAndScheduleExistingAdUseCase,
)
from src.application.use_cases.publication.get_user import GetUserPublicationsUseCase
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.ports.publication_service.image_processor import ImageProcessor
from src.application.ports.publication_service.service_definition_repo import (
    ServiceDefinitionRepository,
)
from src.application.ports.tasks.task_queue import TaskQueue
from src.application.ports.telegram.telegram_publisher import TelegramPublisher
from src.application.ports.user.user_repo import UserRepository
from src.application.services.notification.notification_service import (
    NotificationService,
)
from src.application.use_cases.ad.approve_urgent_buyout import (
    ApproveUrgentBuyoutUseCase,
)
from src.application.use_cases.ad.archive_ad import ArchiveAdUseCase
from src.application.use_cases.ad.count_ads_by_user import CountAdsByUserUseCase
from src.application.use_cases.ad.create_ad_draft import CreateAdDraftUseCase
from src.application.use_cases.ad.eject_urgent_buyout import RejectUrgentBuyoutUseCase
from src.application.use_cases.ad.ensure_ad_image_ref import EnsureAdImageRefUseCase
from src.application.use_cases.ad.finalize_ad import FinalizeAdUseCase
from src.application.use_cases.ad.find_by_plate import FindAdByPlateUseCase
from src.application.use_cases.ad.get_by_id import GetByIdAdUseCase
from src.application.use_cases.ad.update_ad_content import UpdateAdContentUseCase
from src.application.use_cases.catalog.get_catalog_deferred_publications import (
    GetCatalogDeferredPublicationsUseCase,
)
from src.application.use_cases.notification.notify_admins_urgent import (
    NotifyAdminsAboutUrgentUseCase,
)
from src.application.use_cases.notification.notify_pre_publication_users import (
    NotifyPrePublicationUsersUseCase,
)
from src.application.use_cases.payment.confirm import ConfirmPaymentUseCase
from src.application.use_cases.payment.create import CreatePaymentUseCase
from src.application.use_cases.publication.check_limiter import (
    CheckPublicationLimitUseCase,
)
from src.application.use_cases.publication.create_ad_publication import (
    CreateAndScheduleAdUseCase,
)
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdUseCase,
)
from src.application.use_cases.publication.edit_published import EditPublishedAdUseCase
from src.application.use_cases.publication.get_by_id import GetPublicationByIdUseCase
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationUseCase,
)
from src.application.use_cases.publication.reuse_ad_and_schedule import (
    ReuseAdAndScheduleUseCase,
)
from src.application.use_cases.publication_service.add_service_to_publication import (
    AddServiceToPublicationUseCase,
)
from src.application.use_cases.publication_service.apply_service import (
    ApplyServiceToPublishedUseCase,
)
from src.application.use_cases.publication_service.buy_pre_publication_service import (
    BuyPrePublicationServiceUseCase,
)
from src.application.use_cases.publication_service.buy_publication_service import (
    BuyPublicationServiceUseCase,
)
from src.application.use_cases.service_difinition.get_all import GetAllServicesUseCase
from src.application.use_cases.service_difinition.get_by_id import (
    GetByIdServiceDefinitionUseCase,
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
from src.application.use_cases.region.create import CreateRegionUseCase
from src.application.use_cases.region.get_all import GetAllRegionsUseCase
from src.application.use_cases.region.get_by_id import GegByIdRegionUseCase
from src.application.use_cases.seeds.service_definitions import (
    SeedServiceDefinitionsUseCase,
)
from src.application.use_cases.slots.check_hold import CheckHoldUseCase
from src.application.use_cases.slots.get_calendar import GetCalendarUseCase
from src.application.use_cases.slots.hold_slot import HoldSlotUseCase
from src.application.use_cases.slots.release_hold import ReleaseHoldUseCase
from src.application.use_cases.stats.payment import (
    GetPaymentStatsUseCase,
    GetRegionBreakdownUseCase,
)
from src.application.use_cases.stats.publication import GetPublicationStatsUseCase
from src.application.use_cases.stats.region_schedule import GetRegionScheduleUseCase
from src.application.use_cases.store.add_items import AddStoreItemsUseCase
from src.application.use_cases.store.create import CreateStoreUseCase
from src.application.use_cases.store.delete_items import DeleteStoreItemUseCase
from src.application.use_cases.store.get_by_user import GetUserStoreUseCase
from src.application.use_cases.store.update_items import UpdateStoreItemUseCase
from src.application.use_cases.store.update_store import UpdateStoreUseCase
from src.application.use_cases.user.admin_adjust_balance import (
    AdminAdjustBalanceUseCase,
)
from src.application.use_cases.user.get_admin import GetAdminsUseCase
from src.application.use_cases.user.get_by_id import GetByIdUserUseCase
from src.application.use_cases.user.get_by_tg_id import GetByTgIdUserUseCase
from src.application.use_cases.user.manage_admin import ManageAdminUseCase
from src.application.use_cases.user.register import RegisterUserUseCase
from src.application.use_cases.user.set_block import SetUserBlockUseCase
from src.application.use_cases.user.update import UpdateUserUseCase
from src.core.config import AppSettings
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.region.region_guard import RegionGuard
from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.infrastructure.database.transaction_manager.base import TransactionManager
from src.presentation.telegram.common.custom_message_manager import CustomMessageManager


class UseCasesProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def register_user_use_case(
        self,
        region_guard: RegionGuard,
        user_repo: UserRepository,
        transaction_manager: TransactionManager,
    ) -> RegisterUserUseCase:
        return RegisterUserUseCase(
            region_guard=region_guard,
            user_repo=user_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_by_tg_id_user_use_case(
        self,
        user_repo: UserRepository,
    ) -> GetByTgIdUserUseCase:
        return GetByTgIdUserUseCase(
            user_repo=user_repo,
        )

    @provide
    def get_by_id_user_use_case(
        self,
        user_repo: UserRepository,
    ) -> GetByIdUserUseCase:
        return GetByIdUserUseCase(
            user_repo=user_repo,
        )

    @provide
    def update_user_use_case(
        self,
        user_repo: UserRepository,
        transaction_manager: TransactionManager,
    ) -> UpdateUserUseCase:
        return UpdateUserUseCase(
            user_repo=user_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_all_region_use_case(
        self,
        region_repo: RegionRepository,
    ) -> GetAllRegionsUseCase:
        return GetAllRegionsUseCase(region_repo=region_repo)

    @provide
    def get_by_id_region_use_case(
        self,
        region_repo: RegionRepository,
    ) -> GegByIdRegionUseCase:
        return GegByIdRegionUseCase(region_repo=region_repo)

    @provide
    def create_region_use_case(
        self,
        region_repo: RegionRepository,
        transaction_manager: TransactionManager,
    ) -> CreateRegionUseCase:
        return CreateRegionUseCase(
            region_repo=region_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_caledar_use_case(
        self,
        region_guard: RegionGuard,
        region_repo: RegionRepository,
        booking_repo: SlotBookingRepository,
        converted_repo: SlotConvertedRepository,
        hold_store: SlotHoldStore,
        calendar_builder: CalendarBuilder,
    ) -> GetCalendarUseCase:
        return GetCalendarUseCase(
            region_guard=region_guard,
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
        transaction_manager: TransactionManager,
    ) -> HoldSlotUseCase:
        return HoldSlotUseCase(
            region_repo=region_repo,
            calendar_builder=calendar_builder,
            reservation_service=reservation_service,
            transaction_manager=transaction_manager,
        )

    @provide
    def confirm_paid_slot_and_schedule_publication_use_case(
        self,
        publication_repo: PublicationRepository,
        scheduler: Scheduler,
        reservation_service: SlotReservationService,
        transaction_manager: TransactionManager,
    ) -> ConfirmPaidSlotAndSchedulePublicationUseCase:
        return ConfirmPaidSlotAndSchedulePublicationUseCase(
            publication_repo=publication_repo,
            scheduler=scheduler,
            reservation_service=reservation_service,
            transaction_manager=transaction_manager,
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
        transaction_manager: TransactionManager,
    ) -> SelectSlotForPublicationUseCase:
        return SelectSlotForPublicationUseCase(
            publication_repo=publication_repo,
            region_repo=region_repo,
            scheduler=scheduler,
            calendar_builder=calendar_builder,
            time_resolver=time_resolver,
            reservation_service=reservation_service,
            pricing_policy=pricing_policy,
            transaction_manager=transaction_manager,
        )

    @provide
    def confirm_paid_slot_from_balance_use_case(
        self,
        user_repo: UserRepository,
        converted_repo: SlotConvertedRepository,
        transaction_manager: TransactionManager,
    ) -> ConfirmPaidSlotFromBalanceUseCase:
        return ConfirmPaidSlotFromBalanceUseCase(
            user_repo=user_repo,
            converted_repo=converted_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def release_hold_use_case(
        self,
        reservation_service: SlotReservationService,
        transaction_manager: TransactionManager,
    ) -> ReleaseHoldUseCase:
        return ReleaseHoldUseCase(
            reservation_service=reservation_service,
            transaction_manager=transaction_manager,
        )

    @provide
    def add_service_to_publication_use_case(
        self,
        publication_repo: PublicationRepository,
        service_def_repo: ServiceDefinitionRepository,
        transaction_manager: TransactionManager,
    ) -> AddServiceToPublicationUseCase:
        return AddServiceToPublicationUseCase(
            publication_repo=publication_repo,
            service_def_repo=service_def_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def priority_publish_publication_use_case(
        self,
        publication_repo: PublicationRepository,
        scheduler: Scheduler,
        transaction_manager: TransactionManager,
    ) -> PriorityPublishPublicationUseCase:
        return PriorityPublishPublicationUseCase(
            publication_repo=publication_repo,
            scheduler=scheduler,
            transaction_manager=transaction_manager,
        )

    @provide
    def publish_publication_use_case(
        self,
        publication_repo: PublicationRepository,
        ad_repo: AdRepository,
        region_repo: RegionRepository,
        user_repo: UserRepository,
        telegram: TelegramPublisher,
        image_processor: ImageProcessor,
        scheduler: Scheduler,
        renderer: AdTextRenderer,
        time_resolver: PublishTimeResolver,
        transaction_manager: TransactionManager,
    ) -> PublishPublicationUseCase:
        return PublishPublicationUseCase(
            publication_repo=publication_repo,
            ad_repo=ad_repo,
            region_repo=region_repo,
            user_repo=user_repo,
            telegram=telegram,
            image_processor=image_processor,
            scheduler=scheduler,
            renderer=renderer,
            time_resolver=time_resolver,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_user_publications_use_case(
        self,
        publication_repo: PublicationRepository,
    ) -> GetUserPublicationsUseCase:
        return GetUserPublicationsUseCase(publication_repo=publication_repo)

    @provide
    def edit_published_ad_use_case(
        self,
        ad_repo: AdRepository,
        publication_repo: PublicationRepository,
        region_repo: RegionRepository,
        telegram: TelegramPublisher,
        renderer: AdTextRenderer,
        transaction_manager: TransactionManager,
    ) -> EditPublishedAdUseCase:
        return EditPublishedAdUseCase(
            ad_repo=ad_repo,
            publication_repo=publication_repo,
            region_repo=region_repo,
            telegram=telegram,
            renderer=renderer,
            transaction_manager=transaction_manager,
        )

    @provide
    def buy_publication_service_use_case(
        self,
        user_repo: UserRepository,
        publication_repo: PublicationRepository,
        service_def_repo: ServiceDefinitionRepository,
        transaction_manager: TransactionManager,
    ) -> BuyPublicationServiceUseCase:
        return BuyPublicationServiceUseCase(
            user_repo=user_repo,
            publication_repo=publication_repo,
            service_def_repo=service_def_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def buy_pre_publication_service_use_case(
        self,
        user_repo: UserRepository,
        service_def_repo: ServiceDefinitionRepository,
        transaction_manager: TransactionManager,
    ) -> BuyPrePublicationServiceUseCase:
        return BuyPrePublicationServiceUseCase(
            user_repo=user_repo,
            service_def_repo=service_def_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_publication_by_id_use_case(
        self,
        publication_repo: PublicationRepository,
    ) -> GetPublicationByIdUseCase:
        return GetPublicationByIdUseCase(publication_repo=publication_repo)

    @provide
    def get_all_services_use_case(
        self,
        service_def_repo: ServiceDefinitionRepository,
    ) -> GetAllServicesUseCase:
        return GetAllServicesUseCase(service_def_repo=service_def_repo)

    @provide
    def unpin_message_use_case(
        self,
        telegram: TelegramPublisher,
    ) -> UnpinMessageUseCase:
        return UnpinMessageUseCase(telegram=telegram)

    @provide
    def ensure_ad_image_ref_use_case(
        self, bot: Bot, message_manager: CustomMessageManager
    ) -> EnsureAdImageRefUseCase:
        return EnsureAdImageRefUseCase(bot=bot, message_manager=message_manager)

    @provide
    def create_ad_draft_use_case(
        self,
        region_guard: RegionGuard,
        ad_repo: AdRepository,
        transaction_manager: TransactionManager,
    ) -> CreateAdDraftUseCase:
        return CreateAdDraftUseCase(
            region_guard=region_guard,
            ad_repo=ad_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def update_ad_content_use_case(
        self, ad_repo: AdRepository, transaction_manager: TransactionManager
    ) -> UpdateAdContentUseCase:
        return UpdateAdContentUseCase(
            ad_repo=ad_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_by_id_ad_use_case(
        self,
        ad_repo: AdRepository,
    ) -> GetByIdAdUseCase:
        return GetByIdAdUseCase(ad_repo=ad_repo)

    @provide
    def finalize_ad_use_case(
        self,
        ad_repo: AdRepository,
    ) -> FinalizeAdUseCase:
        return FinalizeAdUseCase(
            ad_repo=ad_repo,
        )

    @provide
    def find_ad_by_plate_use_case(
        self,
        ad_repo: AdRepository,
    ) -> FindAdByPlateUseCase:
        return FindAdByPlateUseCase(
            ad_repo=ad_repo,
        )

    @provide
    def archive_ad_use_case(
        self,
        ad_repo: AdRepository,
        publication_repo: PublicationRepository,
        task_queue: TaskQueue,
        transaction_manager: TransactionManager,
    ) -> ArchiveAdUseCase:
        return ArchiveAdUseCase(
            ad_repo=ad_repo,
            publication_repo=publication_repo,
            task_queue=task_queue,
            transaction_manager=transaction_manager,
        )

    @provide
    def count_ads_by_user_use_case(
        self, ad_repo: AdRepository
    ) -> CountAdsByUserUseCase:
        return CountAdsByUserUseCase(ad_repo=ad_repo)

    @provide
    def create_publication_from_ad_use_case(
        self,
        ad_repo: AdRepository,
        publication_repo: PublicationRepository,
        transaction_manager: TransactionManager,
    ) -> CreatePublicationFromAdUseCase:
        return CreatePublicationFromAdUseCase(
            ad_repo=ad_repo,
            publication_repo=publication_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def check_publication_limit_use_case(
        self,
        region_guard: RegionGuard,
        publication_repo: PublicationRepository,
        ad_repo: AdRepository,
        region_repo: RegionRepository,
    ) -> CheckPublicationLimitUseCase:
        return CheckPublicationLimitUseCase(
            region_guard=region_guard,
            publication_repo=publication_repo,
            ad_repo=ad_repo,
            region_repo=region_repo,
        )

    @provide
    def create_and_schedule_use_case(
        self,
        create_draft: CreateAdDraftUseCase,
        update_content: UpdateAdContentUseCase,
        finalize_ad: FinalizeAdUseCase,
        create_publication: CreatePublicationFromAdUseCase,
        select_slot: SelectSlotForPublicationUseCase,
    ) -> CreateAndScheduleAdUseCase:
        return CreateAndScheduleAdUseCase(
            create_draft=create_draft,
            update_content=update_content,
            finalize_ad=finalize_ad,
            create_publication=create_publication,
            select_slot=select_slot,
        )

    @provide
    def finalize_and_schedule_existing_ad_use_case(
        self,
        finalize_ad: FinalizeAdUseCase,
        create_publication: CreatePublicationFromAdUseCase,
        select_slot: SelectSlotForPublicationUseCase,
    ) -> FinalizeAndScheduleExistingAdUseCase:
        return FinalizeAndScheduleExistingAdUseCase(
            finalize_ad=finalize_ad,
            create_publication=create_publication,
            select_slot=select_slot,
        )

    @provide
    def check_hold_use_case(
        self, hold_store: SlotHoldStore, converted_repo: SlotConvertedRepository
    ) -> CheckHoldUseCase:
        return CheckHoldUseCase(
            hold_store=hold_store,
            converted_repo=converted_repo,
        )

    @provide
    def reuse_ad_and_schedule_use_case(
        self,
        create_publication: CreatePublicationFromAdUseCase,
        select_slot: SelectSlotForPublicationUseCase,
    ) -> ReuseAdAndScheduleUseCase:
        return ReuseAdAndScheduleUseCase(
            create_publication=create_publication,
            select_slot=select_slot,
        )

    @provide
    def create_payment_use_case(
        self,
        payment_repo: PaymentRepository,
        user_repo: UserRepository,
        provider_registry: PaymentProviderRegistry,
        transaction_manager: TransactionManager,
    ) -> CreatePaymentUseCase:
        return CreatePaymentUseCase(
            payment_repo=payment_repo,
            user_repo=user_repo,
            provider_registry=provider_registry,
            transaction_manager=transaction_manager,
        )

    @provide
    def confirm_payment_use_case(
        self,
        payment_repo: PaymentRepository,
        user_repo: UserRepository,
        publication_repo: PublicationRepository,
        service_def_repo: ServiceDefinitionRepository,
        confirm_paid_slot: ConfirmPaidSlotAndSchedulePublicationUseCase,
        apply_service_to_published: ApplyServiceToPublishedUseCase,
        priority_publish: PriorityPublishPublicationUseCase,
        reservation_service: SlotReservationService,
        notification_service: NotificationService,
        teleporter: DialogTeleporter,
        transaction_manager: TransactionManager,
    ) -> ConfirmPaymentUseCase:
        return ConfirmPaymentUseCase(
            payment_repo=payment_repo,
            user_repo=user_repo,
            publication_repo=publication_repo,
            service_def_repo=service_def_repo,
            confirm_paid_slot=confirm_paid_slot,
            apply_service_to_published=apply_service_to_published,
            priority_publish=priority_publish,
            reservation_service=reservation_service,
            notification_service=notification_service,
            teleporter=teleporter,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_payment_by_external_id_use_case(
        self,
        payment_repo: PaymentRepository,
    ) -> GetPaymentByExternalIdUseCase:
        return GetPaymentByExternalIdUseCase(
            payment_repo=payment_repo,
        )

    @provide
    def mark_payment_failed_use_case(
        self,
        payment_repo: PaymentRepository,
        transaction_manager: TransactionManager,
    ) -> MarkPaymentFailedUseCase:
        return MarkPaymentFailedUseCase(
            payment_repo=payment_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_by_id_service_definition_use_case(
        self,
        service_def_repo: ServiceDefinitionRepository,
    ) -> GetByIdServiceDefinitionUseCase:
        return GetByIdServiceDefinitionUseCase(
            service_def_repo=service_def_repo,
        )

    @provide
    def seed_service_definitons_use_case(
        self,
        service_def_repo: ServiceDefinitionRepository,
        transaction_manager: TransactionManager,
    ) -> SeedServiceDefinitionsUseCase:
        return SeedServiceDefinitionsUseCase(
            service_def_repo=service_def_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def apply_service_to_published_use_case(
        self,
        publication_repo: PublicationRepository,
        ad_repo: AdRepository,
        region_repo: RegionRepository,
        user_repo: UserRepository,
        telegram: TelegramPublisher,
        image_processor: ImageProcessor,
        renderer: AdTextRenderer,
        scheduler: Scheduler,
        time_resolver: PublishTimeResolver,
        transaction_manager: TransactionManager,
    ) -> ApplyServiceToPublishedUseCase:
        return ApplyServiceToPublishedUseCase(
            publication_repo=publication_repo,
            ad_repo=ad_repo,
            region_repo=region_repo,
            user_repo=user_repo,
            telegram=telegram,
            image_processor=image_processor,
            renderer=renderer,
            scheduler=scheduler,
            time_resolver=time_resolver,
            transaction_manager=transaction_manager,
        )

    @provide
    def notify_admins_urgent_use_case(
        self,
        ad_repo: AdRepository,
        notification_service: NotificationService,
    ) -> NotifyAdminsAboutUrgentUseCase:
        return NotifyAdminsAboutUrgentUseCase(
            ad_repo=ad_repo,
            notification_service=notification_service,
        )

    @provide
    def notify_pre_publication_users_use_case(
        self,
        ad_repo: AdRepository,
        user_repo: UserRepository,
        notification_service: NotificationService,
    ) -> NotifyPrePublicationUsersUseCase:
        return NotifyPrePublicationUsersUseCase(
            ad_repo=ad_repo,
            user_repo=user_repo,
            notification_service=notification_service,
        )

    @provide
    def approve_urgent_buyout_use_case(
        self,
        ad_repo: AdRepository,
        task_queue: TaskQueue,
        transaction_manager: TransactionManager,
    ) -> ApproveUrgentBuyoutUseCase:
        return ApproveUrgentBuyoutUseCase(
            ad_repo=ad_repo,
            task_queue=task_queue,
            transaction_manager=transaction_manager,
        )

    @provide
    def reject_urgnet_buyout_use_case(
        self,
        ad_repo: AdRepository,
        transaction_manager: TransactionManager,
    ) -> RejectUrgentBuyoutUseCase:
        return RejectUrgentBuyoutUseCase(
            ad_repo=ad_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_catalog_deferred_publications_use_case(
        self,
        region_guard: RegionGuard,
        ad_repo: AdRepository,
        publication_repo: PublicationRepository,
        settings: AppSettings,
    ) -> GetCatalogDeferredPublicationsUseCase:
        return GetCatalogDeferredPublicationsUseCase(
            region_guard=region_guard,
            ad_repo=ad_repo,
            publication_repo=publication_repo,
            settings=settings,
        )

    @provide
    def get_user_store_use_case(
        self,
        ad_repo: AdRepository,
    ) -> GetUserStoreUseCase:
        return GetUserStoreUseCase(ad_repo=ad_repo)

    @provide
    def create_store_use_case(
        self,
        region_guard: RegionGuard,
        ad_repo: AdRepository,
        transaction_manager: TransactionManager,
    ) -> CreateStoreUseCase:
        return CreateStoreUseCase(
            region_guard=region_guard,
            ad_repo=ad_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def add_store_items_use_case(
        self,
        ad_repo: AdRepository,
        transaction_manager: TransactionManager,
    ) -> AddStoreItemsUseCase:
        return AddStoreItemsUseCase(
            ad_repo=ad_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def update_store_use_case(
        self,
        ad_repo: AdRepository,
        transaction_manager: TransactionManager,
    ) -> UpdateStoreUseCase:
        return UpdateStoreUseCase(
            ad_repo=ad_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def update_store_item_use_case(
        self,
        ad_repo: AdRepository,
        transaction_manager: TransactionManager,
    ) -> UpdateStoreItemUseCase:
        return UpdateStoreItemUseCase(
            ad_repo=ad_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def delete_store_item_use_case(
        self,
        ad_repo: AdRepository,
        transaction_manager: TransactionManager,
    ) -> DeleteStoreItemUseCase:
        return DeleteStoreItemUseCase(
            ad_repo=ad_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def update_region_setting_use_case(
        self,
        region_repo: RegionRepository,
        transaction_manager: TransactionManager,
    ) -> UpdateRegionSettingsUseCase:
        return UpdateRegionSettingsUseCase(
            region_repo=region_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def update_region_metadata_use_case(
        self,
        region_repo: RegionRepository,
        transaction_manager: TransactionManager,
    ) -> UpdateRegionMetadataUseCase:
        return UpdateRegionMetadataUseCase(
            region_repo=region_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def toggle_region_status_use_case(
        self,
        region_repo: RegionRepository,
        transaction_manager: TransactionManager,
    ) -> ToggleRegionStatusUseCase:
        return ToggleRegionStatusUseCase(
            region_repo=region_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def update_service_use_case(
        self,
        service_repo: ServiceDefinitionRepository,
        transaction_manager: TransactionManager,
    ) -> UpdateServiceUseCase:
        return UpdateServiceUseCase(
            service_repo=service_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def toggle_service_status_use_case(
        self,
        service_repo: ServiceDefinitionRepository,
        transaction_manager: TransactionManager,
    ) -> ToggleServiceStatusUseCase:
        return ToggleServiceStatusUseCase(
            service_repo=service_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def admin_adjust_balance_use_case(
        self,
        user_repo: UserRepository,
        transaction_manager: TransactionManager,
    ) -> AdminAdjustBalanceUseCase:
        return AdminAdjustBalanceUseCase(
            user_repo=user_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def set_user_block_use_case(
        self,
        user_repo: UserRepository,
        block_cache: BlockCache,
        transaction_manager: TransactionManager,
    ) -> SetUserBlockUseCase:
        return SetUserBlockUseCase(
            user_repo=user_repo,
            block_cache=block_cache,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_admins_use_case(
        self,
        user_repo: UserRepository,
    ) -> GetAdminsUseCase:
        return GetAdminsUseCase(
            user_repo=user_repo,
        )

    @provide
    def manage_admin_use_case(
        self,
        user_repo: UserRepository,
        transaction_manager: TransactionManager,
    ) -> ManageAdminUseCase:
        return ManageAdminUseCase(
            user_repo=user_repo,
            transaction_manager=transaction_manager,
        )

    @provide
    def execute_mailing_use_case(
        self,
        user_repo: UserRepository,
        region_repo: RegionRepository,
        notification_service: NotificationService,
    ) -> ExecuteMailingUseCase:
        return ExecuteMailingUseCase(
            user_repo=user_repo,
            region_repo=region_repo,
            notification_service=notification_service,
        )

    @provide
    def enqueue_mailing_use_case(
        self,
        task_queue: TaskQueue,
    ) -> EnqueueMailingUseCase:
        return EnqueueMailingUseCase(
            task_queue=task_queue,
        )

    @provide
    def get_payment_stats_use_case(
        self,
        payment_repo: PaymentRepository,
    ) -> GetPaymentStatsUseCase:
        return GetPaymentStatsUseCase(
            payment_repo=payment_repo,
        )

    @provide
    def get_region_breakdown_use_case(
        self,
        payment_repo: PaymentRepository,
    ) -> GetRegionBreakdownUseCase:
        return GetRegionBreakdownUseCase(
            payment_repo=payment_repo,
        )

    @provide
    def get_publication_stats_use_case(
        self,
        publication_repo: PublicationRepository,
    ) -> GetPublicationStatsUseCase:
        return GetPublicationStatsUseCase(
            publication_repo=publication_repo,
        )

    @provide
    def get_region_schedule_use_case(
        self,
        publication_repo: PublicationRepository,
        region_repo: RegionRepository,
    ) -> GetRegionScheduleUseCase:
        return GetRegionScheduleUseCase(
            publication_repo=publication_repo,
            region_repo=region_repo,
        )

    @provide
    def cancel_publication_by_admin_use_case(
        self,
        publication_repo: PublicationRepository,
        task_queue: TaskQueue,
        notification_service: NotificationService,
        transaction_manager: TransactionManager,
    ) -> CancelPublicationByAdminUseCase:
        return CancelPublicationByAdminUseCase(
            publication_repo=publication_repo,
            task_queue=task_queue,
            notification_service=notification_service,
            transaction_manager=transaction_manager,
        )

    @provide
    def get_admin_scheduled_catalog_use_case(
        self,
        publication_repo: PublicationRepository,
        ad_repo: AdRepository,
    ) -> GetAdminScheduledCatalogUseCase:
        return GetAdminScheduledCatalogUseCase(
            publication_repo=publication_repo,
            ad_repo=ad_repo,
        )
