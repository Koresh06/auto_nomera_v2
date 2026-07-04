from dataclasses import dataclass

from src.domain.enums.role import UserRole
from src.application.dtos.user import UserDTO
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class GetAdminsCommand(UseCaseRequest):
    pass


@dataclass(kw_only=True)
class GetAdminsUseCase(UseCase[GetAdminsCommand, list[UserDTO]]):
    user_repo: UserRepository

    async def __call__(self, command: GetAdminsCommand) -> list[UserDTO]:
        users = await self.user_repo.get_by_role(UserRole.ADMIN)
        return [UserDTO.from_entity(u) for u in users]
