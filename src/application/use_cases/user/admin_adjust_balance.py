import logging
from dataclasses import dataclass
from decimal import Decimal

from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.balance.balance_ledger import BalanceLedger
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.balance_transaction import BalanceTransaction
from src.domain.enums.balance import BalanceTransactionKind
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class AdminAdjustBalanceCommand(UseCaseRequest):
    user_id: int
    amount: Decimal


@dataclass(kw_only=True)
class AdminAdjustBalanceUseCase(UseCase[AdminAdjustBalanceCommand, UserDTO]):
    user_repo: UserRepository
    ledger: BalanceLedger
    transaction_manager: TransactionManager

    async def __call__(self, command: AdminAdjustBalanceCommand) -> UserDTO:
        if command.amount == 0:
            raise ValueError("Amount must not be zero")

        user = await self.user_repo.get_by_id_for_update(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        if command.amount > 0:
            user.top_up(command.amount)
            kind = BalanceTransactionKind.ADMIN_CREDIT
        else:
            user.charge(-command.amount)
            kind = BalanceTransactionKind.ADMIN_DEBIT

        await self.user_repo.save(user)
        await self.ledger.record(
            BalanceTransaction.of(user, amount=command.amount, kind=kind)
        )
        await self.transaction_manager.commit()

        logger.info(
            f"[AdminAdjustBalance] user_id={command.user_id} "
            f"amount={command.amount} new_balance={user.balance}"
        )
        return UserDTO.from_entity(user)
