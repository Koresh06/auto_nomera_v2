import logging
from dataclasses import dataclass

from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.exceptions.slot_reservation import SlotHoldNotFound, SlotHoldOwnerMismatch
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.value_objects.slot_key import SlotKey

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ReleaseHoldRequest(UseCaseRequest):
    slot: SlotKey
    user_id: int
    ad_id: int | None = None


@dataclass(kw_only=True)
class ReleaseHoldUseCase(UseCase[ReleaseHoldRequest, None]):
    reservation_service: SlotReservationService

    async def __call__(self, command: ReleaseHoldRequest) -> None:
        logger.info(
            f"[ReleaseHold] slot={command.slot.local_day} {command.slot.local_time} "
            f"user_id={command.user_id}"
        )
        try:
            await self.reservation_service.release_hold(
                slot=command.slot,
                user_id=command.user_id,
                ad_id=command.ad_id,
            )
            logger.info("[ReleaseHold:done] slot released")
        except (SlotHoldNotFound, SlotHoldOwnerMismatch) as e:
            logger.info(f"[ReleaseHold:skip] {e.__class__.__name__}")