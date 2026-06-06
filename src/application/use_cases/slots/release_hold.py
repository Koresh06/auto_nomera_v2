import logging
from dataclasses import dataclass

from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.value_objects.slot_key import SlotKey
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ReleaseHoldRequest(UseCaseRequest):
    slot: SlotKey
    user_id: int


@dataclass(kw_only=True)
class ReleaseHoldUseCase(UseCase[ReleaseHoldRequest, None]):
    reservation_service: SlotReservationService
    transaction_manager: TransactionManager

    async def __call__(self, command: ReleaseHoldRequest) -> None:
        logger.info(
            f"[ReleaseHold] slot={command.slot.local_day} {command.slot.local_time} "
            f"user_id={command.user_id}"
        )
        await self.reservation_service.release_hold(
            slot=command.slot,
            user_id=command.user_id,
        )
        logger.info("[ReleaseHold:done] slot released")

        await self.transaction_manager.commit()