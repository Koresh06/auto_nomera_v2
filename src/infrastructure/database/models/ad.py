from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, VARCHAR, Enum as SaEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from src.domain.entities.ad import Ad
from src.domain.enums.ad import AdType, AdStatus
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.store_content import StoreContent, StoreItem

from .base import BaseModel, CreatedAtMixin, UpdatedAtMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models import (
        UserModel,
        RegionModel,
        PublicationModel,
    )


class AdModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
    )
    region_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "regions.id",
            ondelete="CASCADE",
        ),
    )
    ad_type: Mapped[AdType] = mapped_column(SaEnum(AdType))
    status: Mapped[AdStatus] = mapped_column(SaEnum(AdStatus))

    plate_number: Mapped[str | None] = mapped_column(VARCHAR(16), nullable=True)
    city: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(VARCHAR(16), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    shop_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    store_items: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel")
    region: Mapped["RegionModel"] = relationship(
        "RegionModel",
        back_populates="ads",
    )
    publications: Mapped[list["PublicationModel"]] = relationship(
        "PublicationModel",
        back_populates="ad",
    )

    def __repr__(self) -> str:
        return (
            f"AdModel(id={self.id}, ad_type={self.ad_type}, plate={self.plate_number})"
        )

    @classmethod
    def from_entity(cls, ad: "Ad") -> "AdModel":
        model = AdModel(
            user_id=ad.user_id,
            region_id=ad.region_id,
            ad_type=ad.ad_type,
            status=ad.status,
        )
        cls._update_model(model, ad)
        return model

    def to_entity(self) -> "Ad":
        ad = Ad(
            id=self.id,
            user_id=self.user_id,
            region_id=self.region_id,
            ad_type=self.ad_type,
            status=self.status,
        )

        if self.ad_type == AdType.STORE:
            items: list[StoreItem] = []
            for item in self.store_items or []:
                items.append(
                    StoreItem(
                        plate=item["plate"],
                        price=Price(int(item["price"])),
                    )
                )
            if self.shop_name:
                ad.fill_store_content(
                    StoreContent(
                        shop_name=self.shop_name,
                        city=self.city or "",
                        contacts=Contacts(username=self.username, phone=self.phone),
                        items=tuple(items),
                    )
                )
        else:
            if self.plate_number or self.city:
                ad.fill_content(
                    AdContent(
                        plate_number=self.plate_number,
                        city=self.city or "",
                        price=Price(self.price or 0),
                        contacts=Contacts(username=self.username, phone=self.phone),
                        caption=self.caption,
                        image_file_id=self.image_file_id,
                    )
                )

        return ad

    @staticmethod
    def _update_model(model: "AdModel", ad: "Ad") -> None:
        model.ad_type = ad.ad_type
        model.status = ad.status

        if ad.ad_type == AdType.STORE and ad.store_content:
            sc = ad.store_content
            model.shop_name = sc.shop_name
            model.city = sc.city
            model.username = sc.contacts.username
            model.phone = sc.contacts.phone
            model.store_items = [
                {
                    "plate": item.plate,
                    "price": item.price.value,
                }
                for item in sc.items
            ]
            model.plate_number = None
            model.price = None
            model.caption = None
            model.image_file_id = None

        elif ad.content:
            c = ad.content
            model.plate_number = c.plate_number
            model.city = c.city
            model.price = c.price.value
            model.username = c.contacts.username
            model.phone = c.contacts.phone
            model.caption = c.caption
            model.image_file_id = c.image_file_id
            # обнуляем поля магазина
            model.shop_name = None
            model.store_items = None
