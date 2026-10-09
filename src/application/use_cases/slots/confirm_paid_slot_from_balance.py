import logging
from dataclasses import dataclass
from decimal import Decimal

from src.application.exceptions.user import UserNotFoundException
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.exceptions.slot_reservation import SlotAlreadyConverted
from src.domain.value_objects.slot_key import SlotKey
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ConfirmPaidSlotFromBalanceRequest(UseCaseRequest):
    user_id: int
    slot: SlotKey
    amount: Decimal


@dataclass(kw_only=True)
class ConfirmPaidSlotFromBalanceUseCase(
    UseCase[ConfirmPaidSlotFromBalanceRequest, None]
):
    user_repo: UserRepository
    converted_repo: SlotConvertedRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: ConfirmPaidSlotFromBalanceRequest) -> None:
        user = await self.user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        # Проверяем ДО списания средств: тот же класс бага, что уже был
        # исправлен в book_after_payment/select_slot_for_publication/
        # ConfirmPaymentUseCase — слот мог достаться другому пользователю
        # буквально секунду раньше, и charge() без этой проверки списал бы
        # деньги без какого-либо эффекта.
        converted = await self.converted_repo.mark_converted(
            slot=command.slot,
            user_id=command.user_id,
        )
        if not converted:
            owner = await self.converted_repo.get_converted_owner_and_ad(command.slot)
            owner_user_id = owner[0] if owner else None
            if owner_user_id != command.user_id:
                raise SlotAlreadyConverted()
            # тот же пользователь уже сконвертировал слот ранее — идемпотентно

        user.charge(command.amount)
        await self.user_repo.save(user)

        await self.transaction_manager.commit()
        logger.info(
            f"[ConfirmPaidSlotFromBalance:done] user_id={command.user_id} "
            f"slot={command.slot.local_day} {command.slot.local_time} amount={command.amount}"
        )
