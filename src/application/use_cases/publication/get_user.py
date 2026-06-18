from dataclasses import dataclass
import logging

from src.application.dtos.publication import PublicationDTO
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class GetUserPublicationsRequest(UseCaseRequest):
    user_id: int
    region_id: int


@dataclass(kw_only=True)
class GetUserPublicationsUseCase(
    UseCase[GetUserPublicationsRequest, list[PublicationDTO]]
):
    publication_repo: PublicationRepository

    async def __call__(
        self, command: GetUserPublicationsRequest
    ) -> list[PublicationDTO]:
        logger.info(
            f"[GetUserPublications] user_id={command.user_id} region_id={command.region_id}"
        )

        rows = await self.publication_repo.list_by_user(
            user_id=command.user_id,
            region_id=command.region_id,
        )

        return [PublicationDTO.from_entity(pub, plate) for pub, plate in rows]
