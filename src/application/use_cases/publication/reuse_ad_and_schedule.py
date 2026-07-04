import logging
from dataclasses import dataclass

from src.application.dtos.publication import PublicationDTO
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdRequest,
    CreatePublicationFromAdUseCase,
)
from src.application.use_cases.publication.select_slot_for_publication import (
    SelectSlotForPublicationRequest,
    SelectSlotForPublicationUseCase,
)
from src.domain.value_objects.slot_key import SlotKey


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ReuseAdAndScheduleRequest(UseCaseRequest):
    ad_id: int
    slot: SlotKey
    user_id: int


@dataclass(kw_only=True)
class ReuseAdAndScheduleUseCase(UseCase[ReuseAdAndScheduleRequest, PublicationDTO]):
    create_publication: CreatePublicationFromAdUseCase
    select_slot: SelectSlotForPublicationUseCase

    async def __call__(self, command: ReuseAdAndScheduleRequest) -> PublicationDTO:
        logger.info(
            f"[ReuseAdAndSchedule] ad_id={command.ad_id} slot={command.slot.local_day} {command.slot.local_time}"
        )

        pub: PublicationDTO = await self.create_publication(
            CreatePublicationFromAdRequest(ad_id=command.ad_id)
        )
        logger.info(f"[ReuseAdAndSchedule:publication] pub_id={pub.id}")

        await self.select_slot(
            SelectSlotForPublicationRequest(
                publication_id=pub.id,
                slot=command.slot,
                user_id=command.user_id,
                ad_id=command.ad_id,
            )
        )
        logger.info(f"[ReuseAdAndSchedule:done] pub_id={pub.id}")

        return pub
