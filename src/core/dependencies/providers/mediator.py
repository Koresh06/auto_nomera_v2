from dishka import Provider, provide, Scope

from src.application.mediator import Mediator
from src.application.use_cases.miling.enqueue import (
    EnqueueMailingRequest,
    EnqueueMailingUseCase,
)
from src.application.use_cases.miling.execute import (
    ExecuteMailingRequest,
    ExecuteMailingUseCase,
)
from src.application.use_cases.publication.cancel_by_admin import (
    CancelPublicationByAdminRequest,
    CancelPublicationByAdminUseCase,
)
from src.application.use_cases.publication.get_admin_scheduled_catalog import (
    GetAdminScheduledCatalogRequest,
    GetAdminScheduledCatalogUseCase,
)
from src.application.use_cases.region.toggle_status import (
    ToggleRegionStatusCommand,
    ToggleRegionStatusUseCase,
)
from src.application.use_cases.region.update_metadata import (
    UpdateRegionMetadataCommand,
    UpdateRegionMetadataUseCase,
)
from src.application.use_cases.region.update_settings import (
    UpdateRegionSettingsCommand,
    UpdateRegionSettingsUseCase,
)
from src.application.use_cases.service_difinition.toggle_status import (
    ToggleServiceStatusCommand,
    ToggleServiceStatusUseCase,
)
from src.application.use_cases.service_difinition.update import (
    UpdateServiceCommand,
    UpdateServiceUseCase,
)
from src.application.use_cases.slots.confirm_paid_slot_from_balance import (
    ConfirmPaidSlotFromBalanceRequest,
    ConfirmPaidSlotFromBalanceUseCase,
)
from src.application.use_cases.payment.get_by_external_id import (
    GetPaymentByExternalIdRequest,
    GetPaymentByExternalIdUseCase,
)
from src.application.use_cases.payment.mark import (
    MarkPaymentFailedRequest,
    MarkPaymentFailedUseCase,
)
from src.application.use_cases.publication.finalize_and_schedule_existing_ad import (
    FinalizeAndScheduleExistingAdRequest,
    FinalizeAndScheduleExistingAdUseCase,
)
from src.application.use_cases.publication.get_user import (
    GetUserPublicationsRequest,
    GetUserPublicationsUseCase,
)
from src.application.use_cases.ad.approve_urgent_buyout import (
    ApproveUrgentBuyoutRequest,
    ApproveUrgentBuyoutUseCase,
)
from src.application.use_cases.ad.archive_ad import ArchiveAdRequest, ArchiveAdUseCase
from src.application.use_cases.ad.count_ads_by_user import (
    CountAdsByUserRequest,
    CountAdsByUserUseCase,
)
from src.application.use_cases.ad.create_ad_draft import (
    CreateAdDraftRequest,
    CreateAdDraftUseCase,
)
from src.application.use_cases.ad.eject_urgent_buyout import (
    RejectUrgentBuyoutRequest,
    RejectUrgentBuyoutUseCase,
)
from src.application.use_cases.ad.ensure_ad_image_ref import (
    EnsureAdImageRefRequest,
    EnsureAdImageRefUseCase,
)
from src.application.use_cases.ad.finalize_ad import (
    FinalizeAdRequest,
    FinalizeAdUseCase,
)
from src.application.use_cases.ad.find_by_plate import (
    FindAdByPlateRequest,
    FindAdByPlateUseCase,
)
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest, GetByIdAdUseCase
from src.application.use_cases.ad.update_ad_content import (
    UpdateAdContentRequest,
    UpdateAdContentUseCase,
)
from src.application.use_cases.catalog.get_catalog_deferred_publications import (
    GetCatalogDeferredPublicationsRequest,
    GetCatalogDeferredPublicationsUseCase,
)
from src.application.use_cases.notification.notify_admins_urgent import (
    NotifyAdminsAboutUrgentRequest,
    NotifyAdminsAboutUrgentUseCase,
)
from src.application.use_cases.notification.notify_pre_publication_users import (
    NotifyPrePublicationUsersRequest,
    NotifyPrePublicationUsersUseCase,
)
from src.application.use_cases.payment.confirm import (
    ConfirmPaymentRequest,
    ConfirmPaymentUseCase,
)
from src.application.use_cases.payment.create import (
    CreatePaymentRequest,
    CreatePaymentUseCase,
)
from src.application.use_cases.publication.check_limiter import (
    CheckPublicationLimitRequest,
    CheckPublicationLimitUseCase,
)
from src.application.use_cases.publication.create_ad_publication import (
    CreateAndScheduleAdRequest,
    CreateAndScheduleAdUseCase,
)
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdRequest,
    CreatePublicationFromAdUseCase,
)
from src.application.use_cases.publication.edit_published import (
    EditPublishedAdRequest,
    EditPublishedAdUseCase,
)
from src.application.use_cases.publication.get_by_id import (
    GetPublicationByIdRequest,
    GetPublicationByIdUseCase,
)
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
    PublishPublicationUseCase,
)
from src.application.use_cases.publication.reuse_ad_and_schedule import (
    ReuseAdAndScheduleRequest,
    ReuseAdAndScheduleUseCase,
)
from src.application.use_cases.publication_service.add_service_to_publication import (
    AddServiceToPublicationRequest,
    AddServiceToPublicationUseCase,
)
from src.application.use_cases.publication_service.apply_service import (
    ApplyServiceToPublishedRequest,
    ApplyServiceToPublishedUseCase,
)
from src.application.use_cases.publication_service.buy_pre_publication_service import (
    BuyPrePublicationServiceRequest,
    BuyPrePublicationServiceUseCase,
)
from src.application.use_cases.publication_service.buy_publication_service import (
    BuyPublicationServiceRequest,
    BuyPublicationServiceUseCase,
)
from src.application.use_cases.service_difinition.get_all import (
    GetAllServicesRequest,
    GetAllServicesUseCase,
)
from src.application.use_cases.service_difinition.get_by_id import (
    GetByIdServiceDefinitionRequest,
    GetByIdServiceDefinitionUseCase,
)
from src.application.use_cases.publication_service.priority_publish_publication import (
    PriorityPublishPublicationRequest,
    PriorityPublishPublicationUseCase,
)
from src.application.use_cases.publication.confirm_paid_slot_and_schedule_publication import (
    ConfirmPaidSlotAndSchedulePublicationRequest,
    ConfirmPaidSlotAndSchedulePublicationUseCase,
)
from src.application.use_cases.publication.select_slot_for_publication import (
    SelectSlotForPublicationRequest,
    SelectSlotForPublicationUseCase,
)
from src.application.use_cases.publication_service.unpin_message import (
    UnpinMessageRequest,
    UnpinMessageUseCase,
)
from src.application.use_cases.region.create import (
    CreateRegionCommand,
    CreateRegionUseCase,
)
from src.application.use_cases.region.get_all import (
    GetAllRegionsUseCase,
    GetRegionsRequest,
)
from src.application.use_cases.region.get_by_id import (
    GegByIdRegionUseCase,
    IdRegionRequest,
)
from src.application.use_cases.seeds.service_definitions import (
    SeedServiceDefinitionsRequest,
    SeedServiceDefinitionsUseCase,
)
from src.application.use_cases.slots.check_hold import (
    CheckHoldRequest,
    CheckHoldUseCase,
)
from src.application.use_cases.slots.get_calendar import (
    GetCalendarRequest,
    GetCalendarUseCase,
)
from src.application.use_cases.slots.hold_slot import HoldSlotRequest, HoldSlotUseCase
from src.application.use_cases.slots.release_hold import (
    ReleaseHoldRequest,
    ReleaseHoldUseCase,
)
from src.application.use_cases.stats.payment import (
    GetPaymentStatsRequest,
    GetPaymentStatsUseCase,
    GetRegionBreakdownRequest,
    GetRegionBreakdownUseCase,
)
from src.application.use_cases.stats.publication import (
    GetPublicationStatsRequest,
    GetPublicationStatsUseCase,
)
from src.application.use_cases.stats.region_schedule import (
    GetRegionScheduleRequest,
    GetRegionScheduleUseCase,
)
from src.application.use_cases.store.add_items import (
    AddStoreItemsRequest,
    AddStoreItemsUseCase,
)
from src.application.use_cases.store.create import (
    CreateStoreRequest,
    CreateStoreUseCase,
)
from src.application.use_cases.store.delete_items import (
    DeleteStoreItemRequest,
    DeleteStoreItemUseCase,
)
from src.application.use_cases.store.get_by_user import (
    GetUserStoreRequest,
    GetUserStoreUseCase,
)
from src.application.use_cases.store.update_items import (
    UpdateStoreItemRequest,
    UpdateStoreItemUseCase,
)
from src.application.use_cases.store.update_store import (
    UpdateStoreRequest,
    UpdateStoreUseCase,
)
from src.application.use_cases.user.admin_adjust_balance import (
    AdminAdjustBalanceCommand,
    AdminAdjustBalanceUseCase,
)
from src.application.use_cases.user.get_admin import GetAdminsCommand, GetAdminsUseCase
from src.application.use_cases.user.get_by_id import GetByIdRequest, GetByIdUserUseCase
from src.application.use_cases.user.get_by_tg_id import (
    GetByTgIdUserUseCase,
    GetTgIdRequest,
)
from src.application.use_cases.user.manage_admin import (
    ManageAdminCommand,
    ManageAdminUseCase,
)
from src.application.use_cases.user.register import (
    UserRegisterRequest,
    RegisterUserUseCase,
)
from src.application.use_cases.user.set_block import (
    SetUserBlockCommand,
    SetUserBlockUseCase,
)
from src.application.use_cases.user.update import UpdateUserRequest, UpdateUserUseCase


class MediatorProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def mediator(
        self,
        user_register_use_case: RegisterUserUseCase,
        get_by_tg_id_user_use_case: GetByTgIdUserUseCase,
        get_by_id_user_use_case: GetByIdUserUseCase,
        update_user_use_case: UpdateUserUseCase,
        get_all_regions_use_case: GetAllRegionsUseCase,
        get_by_id_region_use_case: GegByIdRegionUseCase,
        create_region_use_case: CreateRegionUseCase,
        get_calendar_use_case: GetCalendarUseCase,
        hold_slot_use_case: HoldSlotUseCase,
        confirm_paid_slot_and_schedule_publication_use_case: ConfirmPaidSlotAndSchedulePublicationUseCase,
        select_slot_for_publication_use_case: SelectSlotForPublicationUseCase,
        confirm_paid_slot_from_balance_use_case: ConfirmPaidSlotFromBalanceUseCase,
        release_hold_use_case: ReleaseHoldUseCase,
        add_service_to_publication_use_case: AddServiceToPublicationUseCase,
        priority_publish_publication_use_case: PriorityPublishPublicationUseCase,
        publish_publication_use_case: PublishPublicationUseCase,
        get_user_publications_use_case: GetUserPublicationsUseCase,
        edit_published_ad_use_case: EditPublishedAdUseCase,
        buy_publication_service_use_case: BuyPublicationServiceUseCase,
        buy_pre_publication_service_use_case: BuyPrePublicationServiceUseCase,
        get_publication_by_id_use_case: GetPublicationByIdUseCase,
        get_all_services_use_case: GetAllServicesUseCase,
        unpin_message_use_case: UnpinMessageUseCase,
        ensure_ad_image_ref_use_case: EnsureAdImageRefUseCase,
        create_ad_draft_use_case: CreateAdDraftUseCase,
        update_ad_content_use_case: UpdateAdContentUseCase,
        get_by_id_ad_use_case: GetByIdAdUseCase,
        finalize_ad_use_case: FinalizeAdUseCase,
        find_ad_by_plate_use_case: FindAdByPlateUseCase,
        archive_ad_use_case: ArchiveAdUseCase,
        count_ads_by_user_use_case: CountAdsByUserUseCase,
        create_publication_from_ad_use_case: CreatePublicationFromAdUseCase,
        check_publication_limit_use_case: CheckPublicationLimitUseCase,
        create_and_schedule_use_case: CreateAndScheduleAdUseCase,
        finalize_and_schedule_existing_ad_use_case: FinalizeAndScheduleExistingAdUseCase,
        check_hold_use_case: CheckHoldUseCase,
        reuse_ad_and_schedule_use_case: ReuseAdAndScheduleUseCase,
        create_payment_use_case: CreatePaymentUseCase,
        confirm_payment_use_case: ConfirmPaymentUseCase,
        get_payment_by_external_id_use_case: GetPaymentByExternalIdUseCase,
        mark_payment_failed_use_case: MarkPaymentFailedUseCase,
        get_by_id_service_definition_use_case: GetByIdServiceDefinitionUseCase,
        seed_service_definitons_use_case: SeedServiceDefinitionsUseCase,
        apply_service_to_published_use_case: ApplyServiceToPublishedUseCase,
        notify_admins_urgent_use_case: NotifyAdminsAboutUrgentUseCase,
        notify_pre_publication_users_use_case: NotifyPrePublicationUsersUseCase,
        approve_urgent_buyout_use_case: ApproveUrgentBuyoutUseCase,
        reject_urgnet_buyout_use_case: RejectUrgentBuyoutUseCase,
        get_catalog_deferred_publications_use_case: GetCatalogDeferredPublicationsUseCase,
        get_user_store_use_case: GetUserStoreUseCase,
        create_store_use_case: CreateStoreUseCase,
        add_store_items_use_case: AddStoreItemsUseCase,
        update_store_use_case: UpdateStoreUseCase,
        update_store_item_use_case: UpdateStoreItemUseCase,
        delete_store_item_use_case: DeleteStoreItemUseCase,
        update_region_setting_use_case: UpdateRegionSettingsUseCase,
        update_region_metadata_use_case: UpdateRegionMetadataUseCase,
        toggle_region_status_use_case: ToggleRegionStatusUseCase,
        update_service_use_case: UpdateServiceUseCase,
        toggle_service_status_use_case: ToggleServiceStatusUseCase,
        admin_adjust_balance_use_case: AdminAdjustBalanceUseCase,
        set_user_block_use_case: SetUserBlockUseCase,
        get_admins_use_case: GetAdminsUseCase,
        manage_admin_use_case: ManageAdminUseCase,
        execute_mailing_use_case: ExecuteMailingUseCase,
        enqueue_mailing_use_case: EnqueueMailingUseCase,
        get_payment_stats_use_case: GetPaymentStatsUseCase,
        get_region_breakdown_use_case: GetRegionBreakdownUseCase,
        get_publication_stats_use_case: GetPublicationStatsUseCase,
        get_region_schedule_use_case: GetRegionScheduleUseCase,
        cancel_publication_by_admin_use_case: CancelPublicationByAdminUseCase,
        get_admin_scheduled_catalog_use_case: GetAdminScheduledCatalogUseCase,
    ) -> Mediator:
        mediator = Mediator()

        mediator.register(UserRegisterRequest, user_register_use_case)
        mediator.register(GetTgIdRequest, get_by_tg_id_user_use_case)
        mediator.register(GetByIdRequest, get_by_id_user_use_case)
        mediator.register(UpdateUserRequest, update_user_use_case)
        mediator.register(GetRegionsRequest, get_all_regions_use_case)
        mediator.register(IdRegionRequest, get_by_id_region_use_case)
        mediator.register(CreateRegionCommand, create_region_use_case)

        mediator.register(GetCalendarRequest, get_calendar_use_case)
        mediator.register(HoldSlotRequest, hold_slot_use_case)
        mediator.register(
            ConfirmPaidSlotAndSchedulePublicationRequest,
            confirm_paid_slot_and_schedule_publication_use_case,
        )
        mediator.register(
            SelectSlotForPublicationRequest, select_slot_for_publication_use_case
        )
        mediator.register(
            ConfirmPaidSlotFromBalanceRequest, confirm_paid_slot_from_balance_use_case
        )
        mediator.register(ReleaseHoldRequest, release_hold_use_case)
        mediator.register(
            AddServiceToPublicationRequest, add_service_to_publication_use_case
        )
        mediator.register(
            PriorityPublishPublicationRequest, priority_publish_publication_use_case
        )
        mediator.register(PublishPublicationRequest, publish_publication_use_case)
        mediator.register(GetUserPublicationsRequest, get_user_publications_use_case)
        mediator.register(EditPublishedAdRequest, edit_published_ad_use_case)
        mediator.register(
            BuyPublicationServiceRequest, buy_publication_service_use_case
        )
        mediator.register(
            BuyPrePublicationServiceRequest, buy_pre_publication_service_use_case
        )
        mediator.register(GetPublicationByIdRequest, get_publication_by_id_use_case)
        mediator.register(GetAllServicesRequest, get_all_services_use_case)
        mediator.register(UnpinMessageRequest, unpin_message_use_case)
        mediator.register(EnsureAdImageRefRequest, ensure_ad_image_ref_use_case)
        mediator.register(CreateAdDraftRequest, create_ad_draft_use_case)
        mediator.register(UpdateAdContentRequest, update_ad_content_use_case)
        mediator.register(GetByIdAdRequest, get_by_id_ad_use_case)
        mediator.register(FinalizeAdRequest, finalize_ad_use_case)
        mediator.register(FindAdByPlateRequest, find_ad_by_plate_use_case)
        mediator.register(ArchiveAdRequest, archive_ad_use_case)
        mediator.register(CountAdsByUserRequest, count_ads_by_user_use_case)
        mediator.register(
            CreatePublicationFromAdRequest, create_publication_from_ad_use_case
        )
        mediator.register(
            CheckPublicationLimitRequest, check_publication_limit_use_case
        )
        mediator.register(CreateAndScheduleAdRequest, create_and_schedule_use_case)
        mediator.register(
            FinalizeAndScheduleExistingAdRequest,
            finalize_and_schedule_existing_ad_use_case,
        )
        mediator.register(CheckHoldRequest, check_hold_use_case)
        mediator.register(ReuseAdAndScheduleRequest, reuse_ad_and_schedule_use_case)
        mediator.register(CreatePaymentRequest, create_payment_use_case)
        mediator.register(ConfirmPaymentRequest, confirm_payment_use_case)
        mediator.register(
            GetPaymentByExternalIdRequest, get_payment_by_external_id_use_case
        )
        mediator.register(MarkPaymentFailedRequest, mark_payment_failed_use_case)
        mediator.register(
            GetByIdServiceDefinitionRequest, get_by_id_service_definition_use_case
        )
        mediator.register(
            SeedServiceDefinitionsRequest, seed_service_definitons_use_case
        )
        mediator.register(
            ApplyServiceToPublishedRequest, apply_service_to_published_use_case
        )
        mediator.register(NotifyAdminsAboutUrgentRequest, notify_admins_urgent_use_case)
        mediator.register(
            NotifyPrePublicationUsersRequest, notify_pre_publication_users_use_case
        )
        mediator.register(ApproveUrgentBuyoutRequest, approve_urgent_buyout_use_case)
        mediator.register(RejectUrgentBuyoutRequest, reject_urgnet_buyout_use_case)
        mediator.register(
            GetCatalogDeferredPublicationsRequest,
            get_catalog_deferred_publications_use_case,
        )
        mediator.register(GetUserStoreRequest, get_user_store_use_case)
        mediator.register(CreateStoreRequest, create_store_use_case)
        mediator.register(AddStoreItemsRequest, add_store_items_use_case)
        mediator.register(UpdateStoreRequest, update_store_use_case)
        mediator.register(UpdateStoreItemRequest, update_store_item_use_case)
        mediator.register(DeleteStoreItemRequest, delete_store_item_use_case)
        mediator.register(UpdateRegionSettingsCommand, update_region_setting_use_case)
        mediator.register(UpdateRegionMetadataCommand, update_region_metadata_use_case)
        mediator.register(ToggleRegionStatusCommand, toggle_region_status_use_case)
        mediator.register(ToggleServiceStatusCommand, toggle_service_status_use_case)
        mediator.register(UpdateServiceCommand, update_service_use_case)
        mediator.register(AdminAdjustBalanceCommand, admin_adjust_balance_use_case)
        mediator.register(SetUserBlockCommand, set_user_block_use_case)
        mediator.register(GetAdminsCommand, get_admins_use_case)
        mediator.register(ManageAdminCommand, manage_admin_use_case)
        mediator.register(ExecuteMailingRequest, execute_mailing_use_case)
        mediator.register(EnqueueMailingRequest, enqueue_mailing_use_case)
        mediator.register(GetPaymentStatsRequest, get_payment_stats_use_case)
        mediator.register(GetRegionBreakdownRequest, get_region_breakdown_use_case)
        mediator.register(GetPublicationStatsRequest, get_publication_stats_use_case)
        mediator.register(GetRegionScheduleRequest, get_region_schedule_use_case)
        mediator.register(
            CancelPublicationByAdminRequest, cancel_publication_by_admin_use_case
        )
        mediator.register(
            GetAdminScheduledCatalogRequest, get_admin_scheduled_catalog_use_case
        )

        return mediator
