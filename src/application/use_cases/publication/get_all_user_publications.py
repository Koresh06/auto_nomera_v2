from dataclasses import dataclass

from src.application.dtos.publication import PublicationDTO
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(kw_only=True)
class GetAllUserPublicationsRequest(UseCaseRequest):
    user_id: int
    region_id: int


@dataclass(kw_only=True)
class GetAllUserPublicationsUseCase(
    UseCase[GetAllUserPublicationsRequest, list[PublicationDTO]]
):
    publication_repo: PublicationRepository

    async def __call__(
        self, command: GetAllUserPublicationsRequest
    ) -> list[PublicationDTO]:
        rows = await self.publication_repo.list_all_by_user(
            user_id=command.user_id,
            region_id=command.region_id,
        )
        return [
            PublicationDTO.from_entity(pub, plate_number=plate, shop_name=shop_name)
            for pub, plate, shop_name in rows
        ]
