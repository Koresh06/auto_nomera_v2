from dataclasses import dataclass

from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.telegram.media_virtual_url import build_virtual_plate_url
from src.domain.enums.ad import AdType


@dataclass(frozen=True, eq=False)
class EnsureAdImageRefRequest(UseCaseRequest):
    ad_id: int
    chat_id: int


@dataclass(kw_only=True)
class EnsureAdImageRefUseCase(UseCase[EnsureAdImageRefRequest, None]):
    ad_repo: AdRepository
    region_repo: RegionRepository

    async def __call__(self, command: EnsureAdImageRefRequest) -> None:
        ad = await self.ad_repo.get_by_id(command.ad_id)

        if ad.ad_type == AdType.STORE:
            return

        if ad.content is None:
            raise ValueError("Ad content must exist before ensuring image")

        if ad.content.image_file_id:
            return  # фото уже есть (или уже my://)

        region = await self.region_repo.get_by_id(ad.region_id)
        meta = region.metadata.data if region.metadata else {}
        channel_username = meta.get("channel_username")
        if not channel_username:
            raise ValueError(
                "Region metadata must contain channel_username to generate plate image"
            )

        virtual_url = build_virtual_plate_url(
            plate_number=ad.content.plate_number,
            channel_username=str(channel_username),
            chat_id=command.chat_id,
        )

        # AdContent у нас immutable dataclass, поэтому пересобираем
        c = ad.content
        ad.fill_content(
            type(c)(
                plate_number=c.plate_number,
                city=c.city,
                price=c.price,
                contacts=c.contacts,
                caption=c.caption,
                image_file_id=virtual_url,
            )
        )
        await self.ad_repo.save(ad)  # нужно добавить save в порт/реализацию
