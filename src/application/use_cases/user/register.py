from dataclasses import dataclass

from src.domain.services.region.region_guard import RegionGuard
from src.domain.entities.user import User
from src.application.exceptions.user import UserAlreadyExistsException
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class UserRegisterRequest(UseCaseRequest):
    tg_id: int
    region_id: int
    username: str | None
    full_name: str | None


@dataclass(kw_only=True)
class RegisterUserUseCase(UseCase[UserRegisterRequest, None]):
    region_guard: RegionGuard
    user_repo: UserRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: UserRegisterRequest) -> None:
        await self.region_guard.ensure_active(command.region_id)
        existing = await self.user_repo.get_by_tg_id(command.tg_id)
        if existing is not None:
            raise UserAlreadyExistsException()

        user = User.register(
            tg_id=command.tg_id,
            region_id=command.region_id,
            username=command.username,
            full_name=command.full_name,
        )

        await self.user_repo.add(user)
        await self.transaction_manager.commit()
