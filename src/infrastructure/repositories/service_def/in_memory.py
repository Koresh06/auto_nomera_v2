from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType
from src.application.ports.publication_service.service_definition_repo import (
    ServiceDefinitionRepository,
)


class InMemoryServiceDefinitionRepository(ServiceDefinitionRepository):
    def __init__(self) -> None:
        self._definitions: dict[PublicationServiceType, ServiceDefinition] = {}

    async def get_by_type(
        self, service_type: PublicationServiceType
    ) -> ServiceDefinition:
        return self._definitions[service_type]
    
    async def get_all(self) -> list[ServiceDefinition]:
        return list(self._definitions.values())
    
    async def get_all_active(self) -> list[ServiceDefinition]:
        return [s for s in self._definitions.values() if s.is_active]
    
    async def create(self, service: ServiceDefinition) -> ServiceDefinition:
        self._definitions[service.type] = service
        return service
    
    async def update(
        self,
        service_type: PublicationServiceType,
        *,
        title: str | None = None,
        price: int | None = None,
        is_active: bool | None = None,
        description: str | None = None,
    ) -> ServiceDefinition:
        service = self._definitions[service_type]
        if title is not None:
            service.title = title
        if price is not None:
            service.price = price
        if is_active is not None:
            service.is_active = is_active
        if description is not None:
            service.description = description
        return service
