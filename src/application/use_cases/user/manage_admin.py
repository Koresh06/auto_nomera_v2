import logging
from dataclasses import dataclass
from enum import Enum

from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


class AdminAction(str, Enum):
    PROMOTE = "promote"
    REVOKE = "revoke"


@dataclass(frozen=True, eq=False)
class ManageAdminCommand(UseCaseRequest):
    user_id: int
    action: AdminAction


@dataclass(kw_only=True)
class ManageAdminUseCase(UseCase[ManageAdminCommand, UserDTO]):
    user_repo: UserRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: ManageAdminCommand) -> UserDTO:
        user = await self.user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        if command.action == AdminAction.PROMOTE:
            user.promote_to_admin()
        else:
            user.revoke_admin()

        await self.user_repo.save(user)
        await self.transaction_manager.commit()

        logger.info(
            f"[ManageAdmin] user_id={command.user_id} action={command.action} "
            f"role={user.role}"
        )
        return UserDTO.from_entity(user)