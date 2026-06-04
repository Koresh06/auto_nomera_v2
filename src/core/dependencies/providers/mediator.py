from dishka import Provider, provide, Scope

from src.application.mediator import Mediator
from src.application.use_cases.ad.create_ad_draft import (
    CreateAdDraftRequest,
    CreateAdDraftUseCase,
)
from src.application.use_cases.ad.ensure_ad_image_ref import (
    EnsureAdImageRefRequest,
    EnsureAdImageRefUseCase,
)
from src.application.use_cases.ad.finalize_ad import (
    FinalizeAdRequest,
    FinalizeAdUseCase,
)
from src.application.use_cases.ad.update_ad_content import (
    UpdateAdContentRequest,
    UpdateAdContentUseCase,
)
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdRequest,
    CreatePublicationFromAdUseCase,
)
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
    PublishPublicationUseCase,
)
from src.application.use_cases.publication_service.add_service_to_publication import (
    AddServiceToPublicationRequest,
    AddServiceToPublicationUseCase,
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
from src.application.use_cases.region.create import CreateRegionCommand, CreateRegionUseCase
from src.application.use_cases.region.get_all import (
    GetAllRegionsUseCase,
    GetRegionsRequest,
)
from src.application.use_cases.region.get_by_id import GegByIdRegionUseCase, IdRegionRequest
from src.application.use_cases.slots.get_calendar import (
    GetCalendarRequest,
    GetCalendarUseCase,
)
from src.application.use_cases.slots.hold_slot import HoldSlotRequest, HoldSlotUseCase
from src.application.use_cases.slots.release_hold import ReleaseHoldRequest, ReleaseHoldUseCase
from src.application.use_cases.user.get_by_tg_id import (
    GetByTgIdUserUseCase,
    GetTgIdRequest,
)
from src.application.use_cases.user.register import (
    UserRegisterRequest,
    RegisterUserUseCase,
)
from src.application.use_cases.user.update import UpdateUserRequest, UpdateUserUseCase


class MediatorProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def mediator(
        self,
        user_register_use_case: RegisterUserUseCase,
        get_by_tg_id_user_use_case: GetByTgIdUserUseCase,
        update_user_use_case: UpdateUserUseCase,
        get_all_regions_use_case: GetAllRegionsUseCase,
        get_by_id_region_use_case: GegByIdRegionUseCase,
        create_region_use_case: CreateRegionUseCase,
        get_calendar_use_case: GetCalendarUseCase,
        hold_slot_use_case: HoldSlotUseCase,
        confirm_paid_slot_and_schedule_publication_use_case: ConfirmPaidSlotAndSchedulePublicationUseCase,
        select_slot_for_publication_use_case: SelectSlotForPublicationUseCase,
        release_hold_use_case: ReleaseHoldUseCase,
        add_service_to_publication_use_case: AddServiceToPublicationUseCase,
        priority_publish_publication_use_case: PriorityPublishPublicationUseCase,
        publish_publication_use_case: PublishPublicationUseCase,
        unpin_message_use_case: UnpinMessageUseCase,
        ensure_ad_image_ref_use_case: EnsureAdImageRefUseCase,
        create_ad_draft_use_case: CreateAdDraftUseCase,
        update_ad_content_use_case: UpdateAdContentUseCase,
        finalize_ad_use_case: FinalizeAdUseCase,
        create_publication_from_ad_use_case: CreatePublicationFromAdUseCase,
    ) -> Mediator:
        mediator = Mediator()

        mediator.register(UserRegisterRequest, user_register_use_case)
        mediator.register(GetTgIdRequest, get_by_tg_id_user_use_case)
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
            ReleaseHoldRequest,
            release_hold_use_case,
        )
        mediator.register(
            AddServiceToPublicationRequest, add_service_to_publication_use_case
        )
        mediator.register(
            PriorityPublishPublicationRequest, priority_publish_publication_use_case
        )
        mediator.register(PublishPublicationRequest, publish_publication_use_case)
        mediator.register(UnpinMessageRequest, unpin_message_use_case)
        mediator.register(EnsureAdImageRefRequest, ensure_ad_image_ref_use_case)
        mediator.register(CreateAdDraftRequest, create_ad_draft_use_case)
        mediator.register(UpdateAdContentRequest, update_ad_content_use_case)
        mediator.register(FinalizeAdRequest, finalize_ad_use_case)
        mediator.register(
            CreatePublicationFromAdRequest, create_publication_from_ad_use_case
        )

        return mediator
