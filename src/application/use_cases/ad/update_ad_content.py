from dataclasses import dataclass
import logging

from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.ad import AdType
from src.domain.services.ad.plate_validator import validate_plate
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.store_content import StoreContent, StoreItem
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class UpdateAdContentRequest(UseCaseRequest):
    ad_id: int

    # стандартное объявление
    plate_number: str | None = None
    city: str | None = None
    price: Price | None = None
    contacts: Contacts | None = None
    caption: str | None = None
    image_file_id: str | None = None

    # магазин
    shop_name: str | None = None
    store_items: list[tuple[str, Price]] | None = None


@dataclass(kw_only=True)
class UpdateAdContentUseCase(UseCase[UpdateAdContentRequest, None]):
    ad_repo: AdRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: UpdateAdContentRequest) -> None:
        logger.info(f"[UpdateAdContent] ad_id={command.ad_id}")

        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)

        logger.info(
            f"[UpdateAdContent] ad_type={ad.ad_type} current_content={ad.content}"
        )

        if ad.ad_type == AdType.STORE:
            cur = ad.store_content
            shop_name = (
                command.shop_name
                if command.shop_name is not None
                else (cur.shop_name if cur else "")
            )
            city = (
                command.city if command.city is not None else (cur.city if cur else "")
            )
            contacts = (
                command.contacts
                if command.contacts is not None
                else (cur.contacts if cur else Contacts())
            )

            items = cur.items if cur else tuple()
            if command.store_items is not None:
                validated_items = []
                for plate, price in command.store_items:
                    normalized = validate_plate(plate, allow_mask=False)
                    validated_items.append(StoreItem(plate=normalized, price=price))
                items = tuple(validated_items)

            ad.fill_store_content(
                StoreContent(
                    shop_name=shop_name, city=city, contacts=contacts, items=items
                )
            )
            logger.info(
                f"[UpdateAdContent:store] shop={shop_name!r} city={city!r} items={len(items)}"
            )

        else:
            cur = ad.content
            plate = (
                command.plate_number
                if command.plate_number is not None
                else (cur.plate_number if cur else "")
            )
            city = (
                command.city if command.city is not None else (cur.city if cur else "")
            )
            price = (
                command.price
                if command.price is not None
                else (cur.price if cur else Price(0))
            )
            contacts = (
                command.contacts
                if command.contacts is not None
                else (cur.contacts if cur else Contacts())
            )
            caption = (
                command.caption
                if command.caption is not None
                else (cur.caption if cur else None)
            )
            image_file_id = (
                command.image_file_id
                if command.image_file_id is not None
                else (cur.image_file_id if cur else None)
            )

            ad.fill_content(
                AdContent(
                    plate_number=plate,
                    city=city,
                    price=price,
                    contacts=contacts,
                    caption=caption,
                    image_file_id=image_file_id,
                )
            )
            logger.info(
                f"[UpdateAdContent:standard] plate={plate!r} city={city!r} "
                f"price={price.value} contacts={contacts.display!r} image={image_file_id!r}"
            )

        await self.ad_repo.save(ad)
        logger.info(f"[UpdateAdContent:done] ad_id={ad.id}")

        await self.transaction_manager.commit()
