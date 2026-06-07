from dataclasses import dataclass
import logging

from src.application.dtos.publication import PublicationDTO
from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.publication import Publication
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class CreatePublicationFromAdRequest(UseCaseRequest):
    ad_id: int


@dataclass(kw_only=True)
class CreatePublicationFromAdUseCase(
    UseCase[CreatePublicationFromAdRequest, PublicationDTO]
):
    ad_repo: AdRepository
    publication_repo: PublicationRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: CreatePublicationFromAdRequest) -> PublicationDTO:
        logger.info(f"[CreatePublication] ad_id={command.ad_id}")

        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)

        logger.info(
            f"[CreatePublication] ad_type={ad.ad_type} is_ready={ad.is_ready()}"
        )

        if not ad.is_ready():
            raise ValueError("Ad is not ready to publish")

        pub = await self.publication_repo.create(
            Publication(
                ad_id=ad.id,
                region_id=ad.region_id,
            )
        )

        logger.info(f"[CreatePublication:done] pub_id={pub.id} status={pub.status}")

        await self.transaction_manager.commit()

        return PublicationDTO.from_entity(pub)
