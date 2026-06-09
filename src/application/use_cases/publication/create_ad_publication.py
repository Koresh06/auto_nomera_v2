from dataclasses import dataclass
import logging

from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.ad.create_ad_draft import CreateAdDraftRequest, CreateAdDraftUseCase
from src.application.use_cases.ad.finalize_ad import FinalizeAdRequest, FinalizeAdUseCase
from src.application.use_cases.ad.update_ad_content import UpdateAdContentRequest, UpdateAdContentUseCase
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdRequest,
    CreatePublicationFromAdUseCase,
)
from src.application.use_cases.publication.select_slot_for_publication import (
    SelectSlotForPublicationRequest,
    SelectSlotForPublicationUseCase,
)
from src.domain.enums.ad import AdStatus, AdType
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.slot_key import SlotKey


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class CreateAndScheduleAdRequest(UseCaseRequest):
    user_id: int
    region_id: int
    ad_type: AdType
    plate: str
    city: str
    price: Price
    contacts: Contacts
    image_file_id: str | None
    slot: SlotKey
    chat_id: int


@dataclass(kw_only=True)
class CreateAndScheduleAdUseCase(UseCase[CreateAndScheduleAdRequest, PublicationDTO]):
    create_draft: CreateAdDraftUseCase
    update_content: UpdateAdContentUseCase
    finalize_ad: FinalizeAdUseCase
    create_publication: CreatePublicationFromAdUseCase
    select_slot: SelectSlotForPublicationUseCase

    async def __call__(self, command: CreateAndScheduleAdRequest) -> PublicationDTO:
        logger.info(
            f"[CreateAndScheduleAd] user_id={command.user_id} "
            f"region_id={command.region_id} ad_type={command.ad_type} "
            f"slot={command.slot.local_day} {command.slot.local_time}"
        )

        ad: AdDTO = await self.create_draft(
            CreateAdDraftRequest(
                user_id=command.user_id,
                region_id=command.region_id,
                ad_type=command.ad_type,
                status=AdStatus.DRAFT,
            )
        )
        logger.info(f"[CreateAndScheduleAd:draft] ad_id={ad.id}")

        await self.update_content(
            UpdateAdContentRequest(
                ad_id=ad.id,
                plate_number=command.plate,
                city=command.city,
                price=command.price,
                contacts=command.contacts,
                image_file_id=command.image_file_id,
            )
        )
        logger.info(f"[CreateAndScheduleAd:content] ad_id={ad.id}")

        await self.finalize_ad(FinalizeAdRequest(ad_id=ad.id))
        logger.info(f"[CreateAndScheduleAd:finalized] ad_id={ad.id}")

        pub: PublicationDTO = await self.create_publication(
            CreatePublicationFromAdRequest(ad_id=ad.id)
        )
        logger.info(f"[CreateAndScheduleAd:publication] pub_id={pub.id}")

        await self.select_slot(
            SelectSlotForPublicationRequest(
                publication_id=pub.id,
                slot=command.slot,
                user_id=command.user_id,
                ad_id=ad.id,
            )
        )
        logger.info(f"[CreateAndScheduleAd:slot_selected] pub_id={pub.id}")

        logger.info(f"[CreateAndScheduleAd:done] ad_id={ad.id} pub_id={pub.id}")

        return pub