from dataclasses import dataclass

from src.application.dtos.publication import PublicationDTO
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.publication import Publication


@dataclass(frozen=True, eq=False)
class CreatePublicationFromAdRequest(UseCaseRequest):
    ad_id: int


@dataclass(kw_only=True)
class CreatePublicationFromAdUseCase(UseCase[CreatePublicationFromAdRequest, PublicationDTO]):
    ad_repo: AdRepository
    publication_repo: PublicationRepository

    async def __call__(self, command: CreatePublicationFromAdRequest) -> PublicationDTO:
        ad = await self.ad_repo.get_by_id(command.ad_id)

        # Минимальная защита: объявление должно быть заполнено
        if not ad.is_ready():
            raise ValueError("Ad is not ready to publish")

        pub = Publication(
            ad_id=ad.id,
            region_id=ad.region_id,
        )
        await self.publication_repo.create(pub)

        return PublicationDTO(
            id=pub.id,
            ad_id=pub.ad_id,
            region_id=pub.region_id,
            status=pub.status,
        )
