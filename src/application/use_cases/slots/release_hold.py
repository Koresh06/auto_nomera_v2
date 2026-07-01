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

        converted_info = await self.reservation_service.converted_repo.get_converted_owner_and_ad(
            command.slot
        )
        if converted_info is not None:
            converted_user_id, converted_ad_id = converted_info
            if converted_user_id == command.user_id and converted_ad_id is None:
                await self.reservation_service.converted_repo.unmark_converted(
                    slot=command.slot,
                    user_id=command.user_id,
                )
                logger.info(
                    f"[ReleaseHold:unmark_converted] slot={command.slot.local_day} "
                    f"{command.slot.local_time} user_id={command.user_id} "
                    f"— paid but abandoned, keeping funds"
                )

        await self.transaction_manager.commit()
        logger.info("[ReleaseHold:done] slot released")