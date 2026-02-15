from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.ports.publication.publication_repo import PublicationRepository
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

    async def __call__(self, command: AddServiceToPublicationRequest) -> None:
        _ = command.now_utc or datetime.now(timezone.utc)

        publication = await self.publication_repo.get_by_id(command.publication_id)

        service = PublicationService(
            type=command.service_type,
            params=command.params or {},
        )

        publication.add_service(service)
        await self.publication_repo.save(publication)
