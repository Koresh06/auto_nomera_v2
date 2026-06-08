from dataclasses import dataclass
from decimal import Decimal

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.exceptions.service_definition import ServiceNotAvailableException
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication_service.service_definition_repo import ServiceDefinitionRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication_service import PublicationServiceType
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class BuyPublicationServiceRequest(UseCaseRequest):
    publication_id: int
    service_type: PublicationServiceType
    user_id: int
    params: dict | None = None


@dataclass(kw_only=True)
class BuyPublicationServiceUseCase(UseCase[BuyPublicationServiceRequest, None]):
    user_repo: UserRepository
    publication_repo: PublicationRepository
    service_def_repo: ServiceDefinitionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: BuyPublicationServiceRequest) -> None:
        definition = await self.service_def_repo.get_by_type(command.service_type)
        if not definition.is_active:
            raise ServiceNotAvailableException()

        user = await self.user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException
        price = Decimal(definition.price)

        # списываем баланс (мок — просто проверяем)
        user.charge(price)
        await self.user_repo.save(user)

        publication = await self.publication_repo.get_by_id(command.publication_id)
        if publication is None:
            raise PublicationNotFoundException(command.publication_id)
        service = PublicationService(
            type=command.service_type,
            price_paid=definition.price,
            params=command.params or {},
        )
        publication.add_service(service)
        await self.publication_repo.save(publication)

        await self.transaction_manager.commit()