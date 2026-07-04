from dataclasses import dataclass

from src.application.common.unsent import _Unset, UNSET
from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.exceptions.service_definition import (
    ServiceDefinitionNotFoundException,
)
from src.application.ports.publication_service.service_definition_repo import (
    ServiceDefinitionRepository,
)
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class UpdateServiceCommand(UseCaseRequest):
    service_id: int
    title: str | _Unset = UNSET
    price: int | _Unset = UNSET
    duration_days: int | None | _Unset = UNSET
    description: str | None | _Unset = UNSET


@dataclass(kw_only=True)
class UpdateServiceUseCase(UseCase[UpdateServiceCommand, ServiceDefinitionDTO]):
    service_repo: ServiceDefinitionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: UpdateServiceCommand) -> ServiceDefinitionDTO:
        service = await self.service_repo.get_by_id(command.service_id)
        if service is None:
            raise ServiceDefinitionNotFoundException(command.service_id)

        if not isinstance(command.title, _Unset):
            service.update_title(command.title)
        if not isinstance(command.price, _Unset):
            service.update_price(command.price)
        if not isinstance(command.duration_days, _Unset):
            service.update_duration(command.duration_days)
        if not isinstance(command.description, _Unset):
            service.update_description(command.description)

        service = await self.service_repo.save(service)
        await self.transaction_manager.commit()
        return ServiceDefinitionDTO.from_entity(service)
