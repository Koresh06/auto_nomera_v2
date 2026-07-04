import logging
from dataclasses import dataclass
from enum import Enum

from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.cache.block import BlockCache
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


class BlockAction(str, Enum):
    BLOCK_USER = "block_user"
    UNBLOCK_USER = "unblock_user"
    BLOCK_PAYMENTS = "block_payments"
    UNBLOCK_PAYMENTS = "unblock_payments"


@dataclass(frozen=True, eq=False)
class SetUserBlockCommand(UseCaseRequest):
    user_id: int
    action: BlockAction


@dataclass(kw_only=True)
class SetUserBlockUseCase(UseCase[SetUserBlockCommand, UserDTO]):
    user_repo: UserRepository
    block_cache: BlockCache
    transaction_manager: TransactionManager

    async def __call__(self, command: SetUserBlockCommand) -> UserDTO:
        user = await self.user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        match command.action:
            case BlockAction.BLOCK_USER:
                user.block()
            case BlockAction.UNBLOCK_USER:
                user.unblock()
            case BlockAction.BLOCK_PAYMENTS:
                user.block_payments()
            case BlockAction.UNBLOCK_PAYMENTS:
                user.unblock_payments()

        await self.user_repo.save(user)
        await self.transaction_manager.commit()

        await self.block_cache.set_flags(
            user.tg_id,
            is_blocked=user.is_blocked,
            is_payment_blocked=user.is_payment_blocked,
        )

        logger.info(
            f"[SetUserBlock] user_id={command.user_id} action={command.action} "
            f"is_blocked={user.is_blocked} is_payment_blocked={user.is_payment_blocked}"
        )
        return UserDTO.from_entity(user)
