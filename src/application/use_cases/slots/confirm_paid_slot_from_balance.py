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
        user = await self.user_repo.get_by_id_for_update(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        # Проверяем ДО списания средств: тот же класс бага, что уже был
        # исправлен в book_after_payment/select_slot_for_publication/
        # ConfirmPaymentUseCase — слот мог достаться другому пользователю
        # буквально секунду раньше, и charge() без этой проверки списал бы
        # деньги без какого-либо эффекта.
        # Строка пользователя заблокирована (get_by_id_for_update), поэтому
        # повторный запрос того же пользователя (двойной тап) дождётся конца
        # этой транзакции и увидит уже оформленный слот. Раньше повтор
        # проходил mark_converted (тот же владелец — upsert успешен) и
        # списывал деньги второй раз.
        owner = await self.converted_repo.get_converted_owner_and_ad(command.slot)
        if owner is not None:
            if owner[0] != command.user_id:
                raise SlotAlreadyConverted()
            logger.info(
                f"[ConfirmPaidSlotFromBalance:already_paid] user_id={command.user_id} "
                f"slot={command.slot.local_day} {command.slot.local_time}"
            )
            return

        converted = await self.converted_repo.mark_converted(
            slot=command.slot,
            user_id=command.user_id,
        )
        if not converted:
            # слот успел оформить другой пользователь между проверкой и вставкой
            raise SlotAlreadyConverted()

        user.charge(command.amount)
        await self.user_repo.save(user)

        await self.transaction_manager.commit()
        logger.info(
            f"[ConfirmPaidSlotFromBalance:done] user_id={command.user_id} "
            f"slot={command.slot.local_day} {command.slot.local_time} amount={command.amount}"
        )
