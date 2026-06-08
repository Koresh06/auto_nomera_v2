import logging
from dataclasses import dataclass
from decimal import Decimal

from src.application.exceptions.user import UserNotFoundException
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class TopUpBalanceRequest(UseCaseRequest):
    user_id: int
    amount: Decimal
    payment_id: str | None = None  # id транзакции от платёжной системы


@dataclass(kw_only=True)
class TopUpBalanceUseCase(UseCase[TopUpBalanceRequest, None]):
    user_repo: UserRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: TopUpBalanceRequest) -> None:
        logger.info(
            f"[TopUpBalance] user_id={command.user_id} "
            f"amount={command.amount} payment_id={command.payment_id}"
        )

        if command.amount <= Decimal("0"):
            raise ValueError("Amount must be positive")

        user = await self.user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        user.top_up(command.amount)
        await self.user_repo.save(user)
        await self.transaction_manager.commit()

        logger.info(
            f"[TopUpBalance:done] user_id={command.user_id} "
            f"new_balance={user.balance}"
        )