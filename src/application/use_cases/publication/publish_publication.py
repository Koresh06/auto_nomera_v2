from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication_service.image_processor import ImageProcessor
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.ports.telegram.telegram_publisher import TelegramPublisher
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, eq=False)
class PublishPublicationRequest(UseCaseRequest):
    publication_id: int
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class PublishPublicationUseCase(UseCase[PublishPublicationRequest, None]):
    publication_repo: PublicationRepository
    ad_repo: AdRepository
    region_repo: RegionRepository

    telegram: TelegramPublisher
    image_processor: ImageProcessor
    scheduler: Scheduler

    renderer: AdTextRenderer
    time_resolver: PublishTimeResolver

    async def __call__(self, command: PublishPublicationRequest) -> None:
        now = command.now_utc or datetime.now(timezone.utc)

        pub = await self.publication_repo.get_by_id(command.publication_id)

        # уже опубликовано/отменено/замещено — ничего не делаем
        if pub.status in (
            PublicationStatus.PUBLISHED,
            PublicationStatus.CANCELED,
            PublicationStatus.REPLACED,
        ):
            return

        if pub.status == PublicationStatus.SCHEDULED:
            pub.mark_publishing()
        else:
            pub.status = PublicationStatus.PUBLISHING
            pub.touch()

        await self.publication_repo.save(pub)

        ad = await self.ad_repo.get_by_id(pub.ad_id)
        region = await self.region_repo.get_by_id(pub.region_id)

        text = self.renderer.render(ad=ad, region=region)

        image_file_id = None
        if ad.ad_type.value != "store" and ad.content is not None:
            image_file_id = ad.content.image_file_id

        # 1) highlight — делаем рамку перед публикацией
        if pub.has_service(PublicationServiceType.HIGHLIGHT) and image_file_id:
            image_file_id = await self.image_processor.add_red_frame(
                file_id=image_file_id
            )

        if ad.ad_type.value == "store":
            result = await self.telegram.publish_text(
                channel_id=region.channel_id,
                text=text,
            )
        else:
            if not image_file_id:
                pub.mark_failed()
                await self.publication_repo.save(pub)
                return

            result = await self.telegram.publish_photo(
                channel_id=region.channel_id,
                file_id_or_input=image_file_id,
                caption=text,
            )

        message_id = result.message_id

        pub.mark_published(message_id=message_id, published_at_utc=now)
        await self.publication_repo.save(pub)

        # 3) pin — после публикации
        pin_service = _get_active_service(pub, PublicationServiceType.PIN)
        if pin_service is not None:
            await self.telegram.pin_message(
                channel_id=region.channel_id, message_id=message_id
            )

            # время открепления: пока берём из params, потом можно из админки/настроек
            # params: {"days": 3} или {"hours": 24}
            run_at = self.time_resolver.resolve_unpin_time(now, pin_service.params)
            await self.scheduler.schedule_unpin(
                channel_id=region.channel_id, message_id=message_id, run_at_utc=run_at
            )

            pin_service.mark_used()
            await self.publication_repo.save(pub)

        # 4) autopublish — после первой публикации создаём ещё N-1 публикаций
        auto = _get_active_service(pub, PublicationServiceType.AUTOPUBLISH)
        if auto is not None:
            days = int(auto.params.get("days", 0))
            if days > 1:
                await self._create_autopublications(
                    base_pub=pub,
                    ad_id=ad.id,
                    region_id=region.id,
                    days_total=days,
                    region_timezone=region.timezone.value,
                )
            auto.mark_used()
            await self.publication_repo.save(pub)

    async def _create_autopublications(
        self,
        *,
        base_pub: Publication,
        ad_id: int,
        region_id: int,
        days_total: int,
        region_timezone: str,
    ) -> None:
        # base_pub.slot должен быть известен
        if base_pub.slot is None:
            return

        base_slot: SlotKey = base_pub.slot

        # создаём публикации на следующие дни (N-1)
        for i in range(1, days_total):
            next_slot = SlotKey(
                region_id=region_id,
                local_day=base_slot.local_day + timedelta(days=i),
                local_time=base_slot.local_time,
            )

            # publish_at_utc для next_slot считаем через resolver
            # но resolver ждёт Region, а у нас timezone строкой — проще создать временный Region не будем,
            # поэтому можно сделать отдельную функцию, но пока сделаем быстро:
            publish_at_utc = self.time_resolver.resolve_publish_at_utc(
                region_timezone,
                next_slot,
            )

            new_pub = Publication(
                ad_id=ad_id,
                region_id=region_id,
            )
            new_pub.schedule(slot=next_slot, publish_at_utc=publish_at_utc)

            await self.publication_repo.create(new_pub)
            await self.scheduler.schedule_publication(
                publication_id=new_pub.id, run_at_utc=publish_at_utc
            )


def _get_active_service(
    pub: Publication,
    t: PublicationServiceType,
) -> PublicationService | None:
    for s in pub.services:
        if s.type == t and s.status.value == "active":
            return s
    return None



