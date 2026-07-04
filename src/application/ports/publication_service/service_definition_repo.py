from typing import Protocol

from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType


class ServiceDefinitionRepository(Protocol):
    async def get_by_type(
        self, service_type: PublicationServiceType
    ) -> ServiceDefinition: ...

    async def get_all(
        self, is_active: bool | None = None
    ) -> list[ServiceDefinition]: ...

    async def get_all_active(self) -> list[ServiceDefinition]: ...

    async def get_by_id(self, service_id: int) -> ServiceDefinition: ...

    async def create(self, service: ServiceDefinition) -> ServiceDefinition: ...

    async def save(self, service: ServiceDefinition) -> ServiceDefinition: ...
