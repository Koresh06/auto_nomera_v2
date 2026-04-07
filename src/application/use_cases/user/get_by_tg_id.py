from dataclasses import dataclass

from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoudException
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class GetTgIdRequest(UseCaseRequest):
    tg_id: int


@dataclass(kw_only=True)
class GetByTgIdUserUseCase(UseCase[GetTgIdRequest, UserDTO | None]):
    user_repo: UserRepository

    async def __call__(self, command: GetTgIdRequest) -> UserDTO | None:
        user = await self.user_repo.get_by_tg_id(tg_id=command.tg_id)
        if user is None:
            raise UserNotFoudException
        return UserDTO.from_orm(user)
