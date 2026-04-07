from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication_service.service_definition_repo import (
    ServiceDefinitionRepository,
)
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication_service import PublicationServiceType


@dataclass(frozen=True, eq=False)
class AddServiceToPublicationRequest(UseCaseRequest):
    publication_id: int
    service_type: PublicationServiceType
    params: dict | None = None
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class AddServiceToPublicationUseCase(UseCase[AddServiceToPublicationRequest, None]):
    publication_repo: PublicationRepository
    service_def_repo: ServiceDefinitionRepository

    async def __call__(self, command: AddServiceToPublicationRequest) -> None:
        _now = command.now_utc or datetime.now(timezone.utc)

        # 1) проверяем каталог услуг (существует и активна)
        definition = await self.service_def_repo.get_by_type(command.service_type)
        if not definition.is_active:
            raise ValueError("Услуга отключена админом")

        publication = await self.publication_repo.get_by_id(command.publication_id)

        # 2) создаём applied service
        service = PublicationService(
            type=command.service_type,
            params=command.params or {},
        )

        # 3) добавляем в публикацию
        publication.add_service(service)

        await self.publication_repo.save(publication)
