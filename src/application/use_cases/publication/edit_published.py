import logging
from dataclasses import dataclass

from src.application.exceptions.ad import AdNotFoundException
from src.application.exceptions.publication import PublicationNotFoundException
from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.telegram.telegram_publisher import TelegramPublisher
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.ad import Ad
from src.domain.enums.publication import PublicationStatus
from src.domain.exceptions.publication import InvalidPublicationState
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class EditPublishedAdRequest(UseCaseRequest):
    ad_id: int
    publication_id: int
    city: str | None = None
    price: Price | None = None
    contacts: Contacts | None = None
    caption: str | None = None


@dataclass(kw_only=True)
class EditPublishedAdUseCase(UseCase[EditPublishedAdRequest, None]):
    ad_repo: AdRepository
    publication_repo: PublicationRepository
    region_repo: RegionRepository
    telegram: TelegramPublisher
    renderer: AdTextRenderer
    transaction_manager: TransactionManager

    async def __call__(self, command: EditPublishedAdRequest) -> None:
        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)

        pub = await self.publication_repo.get_by_id(command.publication_id)
        if pub is None:
            raise PublicationNotFoundException(command.publication_id)

        if pub.status != PublicationStatus.PUBLISHED:
            raise InvalidPublicationState("Publication must be PUBLISHED to edit")

        if pub.channel_message_id is None:
            raise ValueError("No message_id — cannot edit")

        region = await self.region_repo.get_by_id(pub.region_id)
        if region is None:
            raise RegionNotFoundException(pub.region_id)

        # обновляем контент — только разрешённые поля (без plate)
        await self._update_content(ad, command)
        await self.ad_repo.save(ad)

        # рендерим новый текст и обновляем сообщение в канале
        new_text = self.renderer.render(ad=ad, region=region)
        await self.telegram.edit_caption(
            channel_id=region.channel_id,
            message_id=pub.channel_message_id,
            caption=new_text,
        )

        await self.transaction_manager.commit()
        logger.info(f"[EditPublishedAd:done] ad_id={ad.id} pub_id={pub.id}")

    async def _update_content(self, ad: Ad, command: EditPublishedAdRequest) -> None:
        cur = ad.content
        if cur is None:
            return
        ad.fill_content(
            AdContent(
                plate_number=cur.plate_number, 
                city=command.city if command.city is not None else cur.city,
                price=command.price if command.price is not None else cur.price,
                contacts=(
                    command.contacts if command.contacts is not None else cur.contacts
                ),
                caption=command.caption if command.caption is not None else cur.caption,
                image_file_id=cur.image_file_id,
            )
        )
