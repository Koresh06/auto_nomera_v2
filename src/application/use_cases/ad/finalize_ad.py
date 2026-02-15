from dataclasses import dataclass

from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.ad import AdType
from src.domain.services.ad.plate_validator import validate_plate
from src.infrastructure.telegram.media_virtual_url import build_virtual_plate_url


@dataclass(frozen=True, eq=False)
class FinalizeAdRequest(UseCaseRequest):
    ad_id: int
    chat_id: int  # куда CustomMessageManager сможет отправить временное фото


@dataclass(kw_only=True)
class FinalizeAdUseCase(UseCase[FinalizeAdRequest, None]):
    ad_repo: AdRepository
    region_repo: RegionRepository

    async def __call__(self, command: FinalizeAdRequest) -> None:
        ad = await self.ad_repo.get_by_id(command.ad_id)

        if ad.ad_type == AdType.STORE:
            sc = ad.store_content
            if sc is None:
                raise ValueError("Store content is required")
        
            if not sc.shop_name.strip():
                raise ValueError("Shop name required")
        
            if not sc.city.strip():
                raise ValueError("City required")
        
            if not sc.contacts.strip():
                raise ValueError("Contacts required")
        
            if len(sc.items) == 0:
                raise ValueError("At least one store item required")
        
            # номера уже провалидированы при вводе
            return

        # стандартные объявления
        if ad.content is None:
            raise ValueError("Ad content is required")

        c = ad.content
        if not c.plate_number.strip():
            raise ValueError("Plate number is required")
        if not c.city.strip():
            raise ValueError("City is required")
        if not c.price_text.strip():
            raise ValueError("Price is required")
        if not c.contacts.strip():
            raise ValueError("Contacts are required")

        # allow_mask логика: для BUY можно маску, для SALE/URGENT — нет
        allow_mask = ad.ad_type == AdType.BUY
        validate_plate(c.plate_number, allow_mask=allow_mask)

        # фото обязательно (кроме STORE)
        if not c.image_file_id:
            region = await self.region_repo.get_by_id(ad.region_id)
            meta = region.metadata.data if region.metadata else {}
            channel_username = meta.get("channel_username")
            if not channel_username:
                raise ValueError("Region metadata must contain channel_username")

            virtual_url = build_virtual_plate_url(
                plate_number=c.plate_number,
                channel_username=str(channel_username),
                chat_id=command.chat_id,
            )

            # пересобираем content
            ad.fill_content(
                type(c)(
                    plate_number=c.plate_number,
                    city=c.city,
                    price_text=c.price_text,
                    contacts=c.contacts,
                    caption=c.caption,
                    image_file_id=virtual_url,
                )
            )

        await self.ad_repo.save(ad)
