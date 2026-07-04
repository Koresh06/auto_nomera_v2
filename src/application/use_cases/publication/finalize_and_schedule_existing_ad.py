import logging
from dataclasses import dataclass

from src.domain.value_objects.slot_key import SlotKey
from src.application.dtos.publication import PublicationDTO
from src.application.use_cases.ad.finalize_ad import (
    FinalizeAdRequest,
    FinalizeAdUseCase,
)
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdRequest,
    CreatePublicationFromAdUseCase,
)
from src.application.use_cases.publication.select_slot_for_publication import (
    SelectSlotForPublicationRequest,
    SelectSlotForPublicationUseCase,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class FinalizeAndScheduleExistingAdRequest(UseCaseRequest):
    ad_id: int
    slot: SlotKey
    user_id: int
    payment_confirmed: bool = False


@dataclass(kw_only=True)
class FinalizeAndScheduleExistingAdUseCase(
    UseCase[FinalizeAndScheduleExistingAdRequest, PublicationDTO]
):
    finalize_ad: FinalizeAdUseCase
    create_publication: CreatePublicationFromAdUseCase
    select_slot: SelectSlotForPublicationUseCase

    async def __call__(
        self, command: FinalizeAndScheduleExistingAdRequest
    ) -> PublicationDTO:
        logger.info(f"[FinalizeAndScheduleExistingAd] ad_id={command.ad_id}")

        await self.finalize_ad(FinalizeAdRequest(ad_id=command.ad_id))
        logger.info(f"[FinalizeAndScheduleExistingAd:finalized] ad_id={command.ad_id}")

        pub: PublicationDTO = await self.create_publication(
            CreatePublicationFromAdRequest(ad_id=command.ad_id)
        )
        logger.info(f"[FinalizeAndScheduleExistingAd:publication] pub_id={pub.id}")

        await self.select_slot(
            SelectSlotForPublicationRequest(
                publication_id=pub.id,
                slot=command.slot,
                user_id=command.user_id,
                ad_id=command.ad_id,
                payment_confirmed=command.payment_confirmed,
            )
        )
        logger.info(f"[FinalizeAndScheduleExistingAd:done] pub_id={pub.id}")

        return pub
