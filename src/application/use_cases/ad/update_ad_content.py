from dataclasses import dataclass

from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.ad import AdType
from src.domain.services.ad.plate_validator import validate_plate
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.store_content import StoreContent, StoreItem


@dataclass(frozen=True, eq=False)
class UpdateAdContentRequest(UseCaseRequest):
    ad_id: int

    # стандартное объявление
    plate_number: str | None = None
    city: str | None = None
    price_text: str | None = None
    contacts: str | None = None
    caption: str | None = None
    image_file_id: str | None = None

    # магазин
    shop_name: str | None = None
    store_items: list[tuple[str, str]] | None = None  # [(plate, price_text), ...]


@dataclass(kw_only=True)
class UpdateAdContentUseCase(UseCase[UpdateAdContentRequest, None]):
    ad_repo: AdRepository

    async def __call__(self, command: UpdateAdContentRequest) -> None:
        ad = await self.ad_repo.get_by_id(command.ad_id)

        if ad.ad_type == AdType.STORE:
            # берём текущие значения, обновляем только то что пришло
            cur = ad.store_content
            shop_name = command.shop_name or (cur.shop_name if cur else "")
            city = command.city or (cur.city if cur else "")
            contacts = command.contacts or (cur.contacts if cur else "")

            items = cur.items if cur else tuple()
            if command.store_items is not None:
                validated_items = []
            
                for plate, price in command.store_items:
                    normalized = validate_plate(plate, allow_mask=False)
                    validated_items.append(
                        StoreItem(
                            plate=normalized,
                            price_text=price,
                        )
                    )
            
                items = tuple(validated_items)

            ad.fill_store_content(
                StoreContent(
                    shop_name=shop_name,
                    city=city,
                    contacts=contacts,
                    items=items,
                )
            )
        else:
            cur = ad.content
            plate = command.plate_number or (cur.plate_number if cur else "")
            city = command.city or (cur.city if cur else "")
            price = command.price_text or (cur.price_text if cur else "")
            contacts = command.contacts or (cur.contacts if cur else "")
            caption = command.caption if command.caption is not None else (cur.caption if cur else None)
            image_file_id = command.image_file_id if command.image_file_id is not None else (cur.image_file_id if cur else None)

            ad.fill_content(
                AdContent(
                    plate_number=plate,
                    city=city,
                    price_text=price,
                    contacts=contacts,
                    caption=caption,
                    image_file_id=image_file_id,
                )
            )

        await self.ad_repo.save(ad)
