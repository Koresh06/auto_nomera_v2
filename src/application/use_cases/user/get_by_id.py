from dataclasses import dataclass

from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class GetByIdRequest(UseCaseRequest):
    user_id: int


@dataclass(kw_only=True)
class GetByIdUserUseCase(UseCase[GetByIdRequest, UserDTO | None]):
    user_repo: UserRepository

    async def __call__(self, command: GetByIdRequest) -> UserDTO | None:
        user = await self.user_repo.get_by_id(user_id=command.user_id)
        if user is None:
            raise UserNotFoundException()
        return UserDTO.from_entity(user)
