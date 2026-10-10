import logging
from dataclasses import dataclass

from src.application.ports.slots.paid_slot_charge_guard import PaidSlotChargeGuard
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
    charge_guard: PaidSlotChargeGuard
    transaction_manager: TransactionManager

    async def __call__(self, command: ReleaseHoldRequest) -> None:
        logger.info(
            f"[ReleaseHold] slot={command.slot.local_day} "
            f"{command.slot.local_time} user_id={command.user_id}"
        )

        # пользователь отказался от слота — следующий выбор этого слота
        # снова платный, а не «двойной тап»
        await self.charge_guard.release(command.user_id, command.slot)

        await self.reservation_service.release_hold(
            slot=command.slot,
            user_id=command.user_id,
        )

        await self.transaction_manager.commit()

        logger.info("[ReleaseHold:done] slot released")
