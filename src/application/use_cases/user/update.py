from dataclasses import dataclass

from src.application.dtos.user import UpdateUserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class UpdateUserRequest(UseCaseRequest):
    tg_id: int
    data: UpdateUserDTO


@dataclass(kw_only=True)
class UpdateUserUseCase(UseCase[UpdateUserRequest, None]):
    user_repo: UserRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: UpdateUserRequest) -> None:
        user = await self.user_repo.get_by_tg_id(tg_id=command.tg_id)
        if user is None:
            raise UserNotFoundException()

        await self.user_repo.update(tg_id=command.tg_id, data=command.data)
        await self.transaction_manager.commit()
