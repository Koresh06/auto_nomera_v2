import logging
from dataclasses import dataclass
from decimal import Decimal

from src.application.exceptions.user import UserNotFoundException
from src.application.ports.balance.balance_ledger import BalanceLedger
from src.application.ports.slots.paid_slot_charge_guard import PaidSlotChargeGuard
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.balance_transaction import BalanceTransaction
from src.domain.enums.balance import BalanceTransactionKind
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
    UseCase[ConfirmPaidSlotFromBalanceRequest, bool]
):
    """Списывает цену платного слота с баланса. Платный слот не эксклюзивный:
    его можно взять, даже если он уже занят другим пользователем, — каждый
    выбор оплачивается заново.

    Возвращает True, если деньги списаны, и False для второго тапа по той же
    кнопке (деньги уже списал первый)."""

    user_repo: UserRepository
    converted_repo: SlotConvertedRepository
    ledger: BalanceLedger
    charge_guard: PaidSlotChargeGuard
    transaction_manager: TransactionManager

    async def __call__(self, command: ConfirmPaidSlotFromBalanceRequest) -> bool:
        if not await self.charge_guard.try_acquire(command.user_id, command.slot):
            logger.info(
                f"[ConfirmPaidSlotFromBalance:double_tap] user_id={command.user_id} "
                f"slot={command.slot.local_day} {command.slot.local_time}"
            )
            return False

        try:
            user = await self.user_repo.get_by_id_for_update(command.user_id)
            if user is None:
                raise UserNotFoundException(command.user_id)

            # отметка «слот платный» одна на слот: если слот уже занимал
            # другой пользователь, она остаётся за ним — на оплату не влияет
            await self.converted_repo.mark_converted(
                slot=command.slot,
                user_id=command.user_id,
            )

            user.charge(command.amount)
            await self.user_repo.save(user)
            await self.ledger.record(
                BalanceTransaction.of(
                    user,
                    amount=-command.amount,
                    kind=BalanceTransactionKind.SLOT_PURCHASE,
                    region_id=command.slot.region_id,
                    description=(
                        f"Слот {command.slot.local_day:%d.%m.%Y} "
                        f"{command.slot.local_time:%H:%M}"
                    ),
                )
            )

            await self.transaction_manager.commit()
        except BaseException:
            # деньги не списаны — следующий тап должен попробовать снова
            await self.charge_guard.release(command.user_id, command.slot)
            raise

        logger.info(
            f"[ConfirmPaidSlotFromBalance:done] user_id={command.user_id} "
            f"slot={command.slot.local_day} {command.slot.local_time} amount={command.amount}"
        )
        return True
