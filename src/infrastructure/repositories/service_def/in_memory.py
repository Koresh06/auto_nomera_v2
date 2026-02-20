from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType
from src.application.ports.publication_service.service_definition_repo import ServiceDefinitionRepository


class InMemoryServiceDefinitionRepository(ServiceDefinitionRepository):
    def __init__(self) -> None:
        self._definitions: dict[PublicationServiceType, ServiceDefinition] = {}

    async def get_by_type(self, service_type: PublicationServiceType) -> ServiceDefinition:
        return self._definitions[service_type]