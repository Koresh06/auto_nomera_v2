from dataclasses import dataclass
from decimal import Decimal

from src.application.exceptions.user import UserNotFoundException
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class BuyPrePublicationServiceRequest(UseCaseRequest):
    user_id: int
    months: int = 1


@dataclass(kw_only=True)
class BuyPrePublicationServiceUseCase(UseCase[BuyPrePublicationServiceRequest, None]):
    user_repo: UserRepository
    transaction_manager: TransactionManager
    price_per_month: Decimal

    async def __call__(self, command: BuyPrePublicationServiceRequest) -> None:
        user = await self.user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException
        price = self.price_per_month * command.months
        user.charge(price)
        user.activate_pre_publication(months=command.months)
        await self.user_repo.save(user)
        await self.transaction_manager.commit()
