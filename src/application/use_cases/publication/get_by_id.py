from dataclasses import dataclass

from src.application.dtos.publication import PublicationDTO
from src.application.exceptions.publication import PublicationNotFoundException
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class GetPublicationByIdRequest(UseCaseRequest):
    publication_id: int


@dataclass(kw_only=True)
class GetPublicationByIdUseCase(UseCase[GetPublicationByIdRequest, PublicationDTO]):
    publication_repo: PublicationRepository

    async def __call__(self, command: GetPublicationByIdRequest) -> PublicationDTO:
        publication = await self.publication_repo.get_by_id(command.publication_id)
        if publication is None:
            raise PublicationNotFoundException(command.publication_id)
        return PublicationDTO.from_entity(publication)
