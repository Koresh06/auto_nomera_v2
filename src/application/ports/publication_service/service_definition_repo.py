from typing import Protocol

from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType


class ServiceDefinitionRepository(Protocol):
    
    async def get_by_type(
        self,
        service_type: PublicationServiceType,
    ) -> ServiceDefinition: 
        ...
