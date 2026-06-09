from dataclasses import dataclass
from decimal import Decimal

from src.application.exceptions.service_definition import ServiceNotAvailableException
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.publication_service.service_definition_repo import ServiceDefinitionRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.publication_service import PublicationServiceType
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class BuyPrePublicationServiceRequest(UseCaseRequest):
    user_id: int
    months: int = 1


@dataclass(kw_only=True)
class BuyPrePublicationServiceUseCase(UseCase[BuyPrePublicationServiceRequest, None]):
    user_repo: UserRepository
    service_def_repo: ServiceDefinitionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: BuyPrePublicationServiceRequest) -> None:
        definition = await self.service_def_repo.get_by_type(
            PublicationServiceType.PRE_PUBLICATION
        )
        if not definition.is_active:
            raise ServiceNotAvailableException()

        user = await self.user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException

        price = Decimal(definition.price) / 100 * command.months
        user.charge(price)
        user.activate_pre_publication(months=command.months)
        await self.user_repo.save(user)
        await self.transaction_manager.commit()
